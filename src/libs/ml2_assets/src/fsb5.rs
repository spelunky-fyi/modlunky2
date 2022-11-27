use std::collections::HashMap;
use std::io::BufRead;
use std::io::Cursor;
use std::io::Seek;
use std::io::SeekFrom;

use bitreader::BitReader;
use bitreader::BitReaderError;
use byteorder::ReadBytesExt;
use byteorder::LE;
use thiserror::Error;

use crate::vorbis_data::rebuild::rebuild_vorbis;
use crate::vorbis_data::rebuild::RebuildError;

#[derive(Error, Debug)]
pub enum Fsb5Error {
    #[error("Not FSB5 Data.")]
    NotFsb5,

    #[error("RebuildVorbisError")]
    RebuildVorbisError(#[from] RebuildError),

    #[error("WaveError")]
    WaveError(#[from] hound::Error),

    #[error("IoError")]
    IoError(#[from] std::io::Error),

    #[error("BitReaderError")]
    BitReaderError(#[from] BitReaderError),
}

#[derive(Debug)]
pub enum SoundFormat {
    None,
    PCM8,
    PCM16,
    PCM24,
    PCM32,
    PCMFLOAT,
    GCADPCM,
    IMAADPCM,
    VAG,
    HEVAG,
    XMA,
    MPEG,
    CELT,
    AT9,
    XWMA,
    VORBIS,
    Unknown,
}

impl From<u32> for SoundFormat {
    fn from(num: u32) -> Self {
        match num {
            0 => SoundFormat::None,
            1 => SoundFormat::PCM8,
            2 => SoundFormat::PCM16,
            3 => SoundFormat::PCM24,
            4 => SoundFormat::PCM32,
            5 => SoundFormat::PCMFLOAT,
            6 => SoundFormat::GCADPCM,
            7 => SoundFormat::IMAADPCM,
            8 => SoundFormat::VAG,
            9 => SoundFormat::HEVAG,
            10 => SoundFormat::XMA,
            11 => SoundFormat::MPEG,
            12 => SoundFormat::CELT,
            13 => SoundFormat::AT9,
            14 => SoundFormat::XWMA,
            15 => SoundFormat::VORBIS,
            _ => SoundFormat::Unknown,
        }
    }
}

impl SoundFormat {
    pub fn file_extension(&self) -> String {
        match self {
            SoundFormat::VORBIS => "ogg".into(),
            SoundFormat::PCM8 | SoundFormat::PCM16 | SoundFormat::PCM32 => "wav".into(),
            _ => "bin".into(),
        }
    }
}

#[derive(Debug)]
pub struct Fsb5Header {
    pub id: String,
    pub version: u32,
    pub num_tracks: u32,
    pub track_header_size: u32,
    pub name_table_size: u32,
    pub data_size: u32,
    pub mode: SoundFormat,

    pub unknown_buf: [u8; 32],

    pub size: u64,
}

impl Fsb5Header {
    fn from_reader<R: BufRead + Seek>(reader: &mut R) -> Result<Self, Fsb5Error> {
        let mut id_buf = [0u8; 4];
        reader.read_exact(&mut id_buf)?;

        let id = String::from_utf8_lossy(&id_buf);
        if id != "FSB5" {
            return Err(Fsb5Error::NotFsb5);
        }

        let version = reader.read_u32::<LE>()?;
        let num_samples = reader.read_u32::<LE>()?;
        let sample_header_size = reader.read_u32::<LE>()?;
        let name_table_size = reader.read_u32::<LE>()?;
        let data_size = reader.read_u32::<LE>()?;
        let mode = reader.read_u32::<LE>()?;

        let mut unknown_buf = [0u8; 32];
        reader.read_exact(&mut unknown_buf)?;

        let size = reader.stream_position()?;

        Ok(Self {
            id: id.into(),
            version,
            num_tracks: num_samples,
            track_header_size: sample_header_size,
            name_table_size,
            data_size,
            mode: mode.into(),
            unknown_buf,
            size,
        })
    }
}

#[derive(PartialEq, Eq, PartialOrd, Ord, Debug, Hash, Clone)]
pub enum SampleMetadataType {
    Channels,
    Frequency,
    Loop,
    XmsSeek,
    DspCoeff,
    XwmaData,
    VorbisData,
    Unknown(u8),
}

impl From<u8> for SampleMetadataType {
    fn from(num: u8) -> Self {
        match num {
            1 => SampleMetadataType::Channels,
            2 => SampleMetadataType::Frequency,
            3 => SampleMetadataType::Loop,
            6 => SampleMetadataType::XmsSeek,
            7 => SampleMetadataType::DspCoeff,
            10 => SampleMetadataType::XwmaData,
            11 => SampleMetadataType::VorbisData,
            num => SampleMetadataType::Unknown(num),
        }
    }
}

#[derive(Debug)]
pub enum SampleMetadataValue {
    VorbisData { crc32: u32, unknown: Vec<u8> },
    Channels(u8),
    Frequency(u32),
    Loop(u32, u32),
    Unknown(Vec<u8>),
}

impl SampleMetadataValue {
    fn from_reader<R: BufRead + Seek>(
        type_: SampleMetadataType,
        size: u32,
        reader: &mut R,
    ) -> Result<Self, Fsb5Error> {
        match type_ {
            SampleMetadataType::VorbisData => {
                let crc32 = reader.read_u32::<LE>()?;
                let mut unknown = vec![0u8; (size as usize) - 4];
                reader.read_exact(&mut unknown)?;
                Ok(SampleMetadataValue::VorbisData { crc32, unknown })
            }
            SampleMetadataType::Channels => Ok(SampleMetadataValue::Channels(reader.read_u8()?)),
            SampleMetadataType::Frequency => {
                Ok(SampleMetadataValue::Frequency(reader.read_u32::<LE>()?))
            }
            SampleMetadataType::Loop => Ok(SampleMetadataValue::Loop(
                reader.read_u32::<LE>()?,
                reader.read_u32::<LE>()?,
            )),
            _ => {
                let mut unknown = vec![0u8; size as usize];
                reader.read_exact(&mut unknown)?;

                Ok(SampleMetadataValue::Unknown(unknown))
            }
        }
    }
}
#[derive(Debug)]
pub struct Track {
    pub name: String,
    pub frequency: u32,
    pub channels: u8,
    pub data_offset: u32,
    pub samples: u32,
    pub metadata: HashMap<SampleMetadataType, SampleMetadataValue>,
    pub data: Vec<u8>,
}

impl Track {
    fn get_frequency_from_idx(idx: u8) -> u32 {
        match idx {
            1 => 8000,
            2 => 11000,
            3 => 11025,
            4 => 16000,
            5 => 22050,
            6 => 24000,
            7 => 32000,
            8 => 44100,
            9 => 48000,
            _ => 0,
        }
    }

    fn from_reader<R: BufRead + Seek>(mut reader: &mut R) -> Result<Self, Fsb5Error> {
        let packed = reader.read_u64::<LE>()?;
        let packed_bytes = packed.to_be_bytes();
        let mut bit_reader = BitReader::new(&packed_bytes);

        let samples = bit_reader.read_u32(30)?;
        let data_offset = bit_reader.read_u32(28)? * 16;
        let channels = bit_reader.read_u8(1)? + 1;
        let frequency_idx = bit_reader.read_u8(4)?;
        let mut next_chunk = bit_reader.read_bool()?;

        let mut metadata = HashMap::new();
        let data = vec![];

        while next_chunk {
            let packed = reader.read_u32::<LE>()?;
            let packed_bytes = packed.to_be_bytes();
            let mut bit_reader = BitReader::new(&packed_bytes);

            let chunk_type: SampleMetadataType = bit_reader.read_u8(7)?.into();
            let chunk_size = bit_reader.read_u32(24)?;
            next_chunk = bit_reader.read_bool()?;

            metadata.insert(
                chunk_type.clone(),
                SampleMetadataValue::from_reader(chunk_type, chunk_size, &mut reader)?,
            );
        }

        let frequency = if let Some(SampleMetadataValue::Frequency(freq)) =
            metadata.get(&SampleMetadataType::Frequency)
        {
            *freq
        } else {
            Track::get_frequency_from_idx(frequency_idx)
        };

        assert!(frequency != 0);

        Ok(Self {
            name: String::from(""),
            frequency,
            channels,
            data_offset,
            samples,
            metadata,
            data,
        })
    }

    fn rebuild_wav(&self, width: u32) -> Result<Vec<u8>, Fsb5Error> {
        let mut wav = Cursor::new(Vec::with_capacity(
            (self.samples * self.channels as u32 * width) as usize,
        ));
        let size = self.samples * self.channels as u32 * width;
        let spec = hound::WavSpec {
            channels: self.channels as u16,
            sample_rate: self.frequency,
            bits_per_sample: width as u16 * 8,
            sample_format: hound::SampleFormat::Int,
        };

        let mut wav_writer = hound::WavWriter::new(&mut wav, spec)?;

        for offset in (0..size).step_by(width as usize) {
            let offset = offset as usize;
            match width {
                1 => {
                    let sample = self.data[offset] as i8;
                    wav_writer.write_sample(sample)?;
                }
                2 => {
                    let mut bytes = &self.data[offset..offset + (width as usize)];
                    let sample = bytes.read_i16::<LE>()?;
                    wav_writer.write_sample(sample)?;
                }
                4 => {
                    let mut bytes = &self.data[offset..offset + (width as usize)];
                    let sample = bytes.read_i32::<LE>()?;
                    wav_writer.write_sample(sample)?;
                }
                _ => unreachable!(),
            }
        }

        wav_writer.finalize()?;

        Ok(wav.into_inner())
    }

    pub fn rebuild_as(&self, format: &SoundFormat) -> Result<Vec<u8>, Fsb5Error> {
        use SoundFormat::*;

        Ok(match format {
            PCM8 => self.rebuild_wav(1)?,
            PCM16 => self.rebuild_wav(2)?,
            PCM32 => self.rebuild_wav(4)?,
            VORBIS => rebuild_vorbis(self)?,
            _ => unimplemented!("sorry..."),
        })
    }
}

#[derive(Debug)]
pub struct Fsb5 {
    pub header: Fsb5Header,
    pub tracks: Vec<Track>,
}

impl Fsb5 {
    pub fn from_reader<R: BufRead + Seek>(mut reader: &mut R) -> Result<Self, Fsb5Error> {
        let header = Fsb5Header::from_reader(&mut reader)?;
        let mut tracks = Vec::with_capacity(header.num_tracks as usize);

        for _ in 0..header.num_tracks {
            let track = Track::from_reader(&mut reader)?;
            tracks.push(track);
        }

        if header.name_table_size > 0 {
            let name_table_start = reader.stream_position()?;
            let mut sample_name_offsets = Vec::with_capacity(header.num_tracks as usize);

            for _ in 0..header.num_tracks {
                sample_name_offsets.push(reader.read_u32::<LE>()?);
            }

            for idx in 0..header.num_tracks {
                reader.seek(SeekFrom::Start(
                    name_table_start + sample_name_offsets[idx as usize] as u64,
                ))?;
                let mut name = vec![];
                reader.read_until(0, &mut name)?;
                let name = String::from_utf8_lossy(&name[0..name.len() - 1]);
                tracks[idx as usize].name.push_str(&name);
            }
        }

        reader.seek(SeekFrom::Start(
            header.size + header.track_header_size as u64 + header.name_table_size as u64,
        ))?;
        for idx in 0..header.num_tracks {
            let idx = idx as usize;

            let data_start = tracks[idx].data_offset;
            let mut data_end = data_start + header.data_size;

            if (idx as u32) < header.num_tracks - 1 {
                data_end = tracks[idx + 1].data_offset;
            }

            tracks[idx].data.resize((data_end - data_start) as usize, 0);
            let _ = reader.read(&mut tracks[idx].data)?;
        }

        Ok(Self { header, tracks })
    }
}
