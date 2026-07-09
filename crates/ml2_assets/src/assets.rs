use std::io::{Cursor, Write};
use std::{
    collections::HashMap,
    fs::{File, create_dir_all},
    io::{Read, Seek, SeekFrom},
    path::Path,
};

use byteorder::{LE, ReadBytesExt};
use image::codecs::png::{CompressionType, FilterType, PngEncoder};
use image::{ColorType, ImageEncoder, ImageError, Rgba, RgbaImage};
use thiserror::Error;
use zstd::decode_all;

use ml2_chacha::{NasamGenerator, Spel2ChaCha, Spel2ChaChaVersion2};

use crate::files::get_filepath_registry;

const BUNDLE_OFFSET: u64 = 0x400;

#[derive(Error, Debug)]
pub enum AssetError {
    #[error("IoError")]
    IoError(#[from] std::io::Error),

    #[error("DdsError: {0}")]
    DdsError(#[from] ddsfile::Error),

    #[error("ImageError")]
    ImageError(#[from] ImageError),
}

#[derive(Debug)]
pub struct AssetMeta {
    /// Position in the .exe where asset meta is located.
    pub offset: u64,

    /// Length of the filepath
    pub filepath_len: u32,

    /// The hash of the filepath
    pub filepath_hash: Vec<u8>,

    /// Whether the asset is encrypted and compressed
    pub is_encrypted: bool,

    /// Position into the .exe where the data itself is located
    pub asset_offset: u64,

    /// The size of the asset itself.
    pub asset_len: u32,
}

impl AssetMeta {
    pub fn total_size(&self) -> u64 {
        8 // 8 bytes for header (asset_len, filepath_len)
        + self.filepath_len as u64  // The size of the filepath
        + 1  // The byte for whether the asset is encrypted
        + self.asset_len as u64 // The size of the asset
    }

    fn from_handle<T: Seek + Read>(handle: &mut T) -> Result<Option<Self>, AssetError> {
        let offset = handle.stream_position()?;

        let data_len = handle.read_u32::<LE>()?;
        let filepath_len = handle.read_u32::<LE>()?;

        if (data_len, filepath_len) == (0, 0) {
            return Ok(None);
        }

        let asset_len = data_len - 1;
        let mut filepath_hash = vec![0; filepath_len as usize];
        handle.read_exact(&mut filepath_hash)?;

        let is_encrypted = handle.read_u8()? == 1;
        let asset_offset = handle.stream_position()?;

        handle.seek(std::io::SeekFrom::Current(asset_len as i64))?;

        Ok(Some(Self {
            offset,
            filepath_len,
            filepath_hash,
            is_encrypted,
            asset_offset,
            asset_len,
        }))
    }
}

#[derive(Debug)]
pub struct Asset {
    pub meta: AssetMeta,
    pub filepath: Option<Vec<u8>>,
    pub data: Option<Vec<u8>>,
}

fn get_idx_from_mask(idx: Option<u32>) -> usize {
    match idx {
        Some(0xFF) => 0,
        Some(0xFF00) => 1,
        Some(0xFF0000) => 2,
        Some(0xFF000000) => 3,
        _ => 0,
    }
}

impl Asset {
    fn extract<T: Spel2ChaCha>(&self, extract_dir: &Path, chacha: &T) -> Result<(), AssetError> {
        let filepath = match &self.filepath {
            Some(filepath) => filepath,
            None => return Ok(()),
        };

        let mut data = match &self.data {
            Some(data) => data.to_vec(),
            None => return Ok(()),
        };

        let filepath_str: String = String::from_utf8_lossy(filepath).into();
        let mut fullpath = extract_dir.join(filepath_str);

        if let Some(parent) = fullpath.parent() {
            create_dir_all(parent)?;
        }

        if self.meta.is_encrypted {
            data = chacha.decrypt(filepath, &data);
            data = decode_all(&data[..])?;
        }

        if let Some(ext) = fullpath.extension()
            && ext == "DDS"
        {
            let dds = ddsfile::Dds::read(Cursor::new(&data))?;

            let width = dds.get_width();
            let height = dds.get_height();
            let max_size = width * height;
            let mut img = RgbaImage::new(width, height);

            // ddsfile 0.6's `get_data(0)` gate-keeps on `get_format()`, which
            // returns None for the RGBA bitmask layout Spelunky's DDSes use
            // (its `try_from_pixel_format` is stricter than 0.5's was). We
            // don't need the format lookup at all: the pixel loop below reads
            // channel positions straight out of `spf.*_bit_mask`, so raw
            // `dds.data` is enough.
            for (idx, chunk) in dds.data.chunks(4).enumerate() {
                let idx = idx as u32;
                if idx >= max_size {
                    break;
                }
                let x = idx % width;
                let y = idx / width;

                let r = chunk[get_idx_from_mask(dds.header.spf.r_bit_mask)];
                let g = chunk[get_idx_from_mask(dds.header.spf.g_bit_mask)];
                let b = chunk[get_idx_from_mask(dds.header.spf.b_bit_mask)];
                let a = chunk[get_idx_from_mask(dds.header.spf.a_bit_mask)];

                img.put_pixel(x, y, Rgba([r, g, b, a]));
            }

            fullpath.set_extension("png");
            data = Vec::new();
            // Use max-compression PNG so extract output size stays close
            // to libpng defaults. The image crate's default deflate
            // level produces PNGs roughly 2x larger.
            let mut cursor = Cursor::new(&mut data);
            let encoder = PngEncoder::new_with_quality(
                &mut cursor,
                CompressionType::Best,
                FilterType::Adaptive,
            );
            encoder.write_image(
                img.as_raw(),
                img.width(),
                img.height(),
                ColorType::Rgba8.into(),
            )?;
        }

        let mut file = File::create(fullpath)?;
        file.write_all(&data)?;

        Ok(())
    }

    fn load_data<T: Seek + Read>(&mut self, handle: &mut T) -> Result<(), AssetError> {
        handle.seek(SeekFrom::Start(self.meta.asset_offset))?;
        let mut data = vec![0; self.meta.asset_len as usize];
        handle.read_exact(&mut data)?;
        self.data = Some(data);
        Ok(())
    }
}

#[derive(Debug)]
pub struct AssetStore<T: Seek + Read> {
    pub assets: Vec<Asset>,
    handle: T,
    chacha: Spel2ChaChaVersion2,
    registry: HashMap<Vec<u8>, &'static [u8]>,
}

impl<T: Seek + Read> AssetStore<T> {
    pub fn from_handle(mut handle: T) -> Result<Self, AssetError> {
        let mut assets = Vec::new();
        let mut keygen = NasamGenerator::default();

        handle.seek(std::io::SeekFrom::Start(BUNDLE_OFFSET))?;

        while let Some(meta) = AssetMeta::from_handle(&mut handle)? {
            keygen.update(meta.asset_len as u64 + 1);
            assets.push(Asset {
                meta,
                filepath: None,
                data: None,
            });
        }

        let chacha = Spel2ChaChaVersion2::new(keygen.key);
        let registry = get_filepath_registry(&chacha);

        let mut inst = Self {
            assets,
            handle,
            chacha,
            registry,
        };

        inst.populate_filepaths();

        Ok(inst)
    }

    fn populate_filepaths(&mut self) {
        for asset in self.assets.iter_mut() {
            // Try full hash first
            if let Some(filepath) = self.registry.get(&asset.meta.filepath_hash) {
                asset.filepath = Some(filepath.to_vec());
                continue;
            }

            let end = &asset.meta.filepath_hash.iter().rposition(|elem| *elem != 0);
            if let Some(end) = end {
                let key = &asset.meta.filepath_hash[..*end + 1];
                if let Some(filepath) = self.registry.get(key) {
                    asset.filepath = Some(filepath.to_vec());
                }
            }
        }
    }

    pub fn extract(&mut self, extract_dir: &Path) -> Result<(), AssetError> {
        self.extract_with_progress(extract_dir, |_, _| {})
    }

    /// Same as `extract` but calls `on_progress(done, total)` after each
    /// asset writes successfully. `total` is the number of assets that have a
    /// resolvable filepath (the rest are skipped anyway). Consumers should
    /// throttle if they forward this over IPC or a UI channel; the callback
    /// fires roughly a thousand times per full Spel2.exe extraction.
    pub fn extract_with_progress<F>(
        &mut self,
        extract_dir: &Path,
        mut on_progress: F,
    ) -> Result<(), AssetError>
    where
        F: FnMut(usize, usize),
    {
        let total = self.assets.iter().filter(|a| a.filepath.is_some()).count();
        let mut done = 0usize;
        for asset in self.assets.iter_mut() {
            if asset.filepath.is_none() {
                continue;
            }
            asset.load_data(&mut self.handle)?;
            asset.extract(extract_dir, &self.chacha)?;
            done += 1;
            on_progress(done, total);
        }
        Ok(())
    }
}
