use std::collections::HashMap;
use std::io::BufRead;
use std::io::Cursor;
use std::io::Seek;
use std::io::SeekFrom;

use bitreader::BitReader;
use byteorder::ReadBytesExt;
use byteorder::LE;
use riff_io::Entry;

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
    fn from_reader<R: BufRead + Seek>(reader: &mut R) -> Result<Self, ()> {
        let mut id_buf = [0u8; 4];
        reader.read_exact(&mut id_buf).unwrap();

        let id = String::from_utf8_lossy(&id_buf);
        if id != "FSB5" {
            return Err(());
        }

        let version = reader.read_u32::<LE>().unwrap();
        let num_samples = reader.read_u32::<LE>().unwrap();
        let sample_header_size = reader.read_u32::<LE>().unwrap();
        let name_table_size = reader.read_u32::<LE>().unwrap();
        let data_size = reader.read_u32::<LE>().unwrap();
        let mode = reader.read_u32::<LE>().unwrap();

        let mut unknown_buf = [0u8; 32];
        reader.read_exact(&mut unknown_buf).unwrap();

        let size = reader.stream_position().unwrap();

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
    ) -> Result<Self, ()> {
        match type_ {
            SampleMetadataType::VorbisData => {
                let crc32 = reader.read_u32::<LE>().unwrap();
                let mut unknown = vec![0u8; (size as usize) - 4];
                reader.read_exact(&mut unknown).unwrap();
                Ok(SampleMetadataValue::VorbisData { crc32, unknown })
            }
            SampleMetadataType::Channels => {
                Ok(SampleMetadataValue::Channels(reader.read_u8().unwrap()))
            }
            SampleMetadataType::Frequency => Ok(SampleMetadataValue::Frequency(
                reader.read_u32::<LE>().unwrap(),
            )),
            SampleMetadataType::Loop => Ok(SampleMetadataValue::Loop(
                reader.read_u32::<LE>().unwrap(),
                reader.read_u32::<LE>().unwrap(),
            )),
            _ => {
                let mut unknown = vec![0u8; size as usize];
                reader.read_exact(&mut unknown).unwrap();

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

    fn from_reader<R: BufRead + Seek>(mut reader: &mut R) -> Result<Self, ()> {
        let packed = reader.read_u64::<LE>().unwrap();
        let packed_bytes = packed.to_be_bytes();
        let mut bit_reader = BitReader::new(&packed_bytes);

        let samples = bit_reader.read_u32(30).unwrap();
        let data_offset = bit_reader.read_u32(28).unwrap() * 16;
        let channels = bit_reader.read_u8(1).unwrap() + 1;
        let frequency_idx = bit_reader.read_u8(4).unwrap();
        let mut next_chunk = bit_reader.read_bool().unwrap();

        let mut metadata = HashMap::new();
        let data = vec![];

        while next_chunk {
            let packed = reader.read_u32::<LE>().unwrap();
            let packed_bytes = packed.to_be_bytes();
            let mut bit_reader = BitReader::new(&packed_bytes);

            let chunk_type: SampleMetadataType = bit_reader.read_u8(7).unwrap().into();
            let chunk_size = bit_reader.read_u32(24).unwrap();
            next_chunk = bit_reader.read_bool().unwrap();

            metadata.insert(
                chunk_type.clone(),
                SampleMetadataValue::from_reader(chunk_type, chunk_size, &mut reader).unwrap(),
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

    pub fn rebuild_as(&self, format: &SoundFormat) -> Vec<u8> {
        use SoundFormat::*;

        match format {
            PCM8 | PCM16 | PCM32 => {
                let width = match format {
                    PCM8 => 1,
                    PCM16 => 2,
                    PCM32 => 4,
                    _ => unreachable!(),
                };
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

                let mut wav_writer = hound::WavWriter::new(&mut wav, spec).unwrap();

                for offset in (0..size).step_by(width as usize) {
                    let offset = offset as usize;
                    match width {
                        1 => {
                            let sample = self.data[offset] as i8;
                            wav_writer.write_sample(sample).unwrap();
                        }
                        2 => {
                            let mut bytes = &self.data[offset..offset + (width as usize)];
                            let sample = bytes.read_i16::<LE>().unwrap();
                            wav_writer.write_sample(sample).unwrap();
                        }
                        4 => {
                            let mut bytes = &self.data[offset..offset + (width as usize)];
                            let sample = bytes.read_i32::<LE>().unwrap();
                            wav_writer.write_sample(sample).unwrap();
                        }
                        _ => unreachable!(),
                    }
                }

                wav_writer.finalize().unwrap();

                wav.into_inner()
            }
            _ => unimplemented!("sorry..."),
        }
    }
}

#[derive(Debug)]
pub struct Fsb5 {
    pub header: Fsb5Header,
    pub tracks: Vec<Track>,
}

impl Fsb5 {
    fn from_reader<R: BufRead + Seek>(mut reader: &mut R) -> Result<Self, ()> {
        let header = Fsb5Header::from_reader(&mut reader).unwrap();
        let mut tracks = Vec::with_capacity(header.num_tracks as usize);

        for _ in 0..header.num_tracks {
            let track = Track::from_reader(&mut reader).unwrap();
            tracks.push(track);
        }

        if header.name_table_size > 0 {
            let name_table_start = reader.stream_position().unwrap();
            let mut sample_name_offsets = Vec::with_capacity(header.num_tracks as usize);

            for _ in 0..header.num_tracks {
                sample_name_offsets.push(reader.read_u32::<LE>().unwrap());
            }

            for idx in 0..header.num_tracks {
                reader
                    .seek(SeekFrom::Start(
                        name_table_start + sample_name_offsets[idx as usize] as u64,
                    ))
                    .unwrap();
                let mut name = vec![];
                reader.read_until(0, &mut name).unwrap();
                let name = String::from_utf8_lossy(&name[0..name.len() - 1]);
                tracks[idx as usize].name.push_str(&name);
            }
        }

        reader
            .seek(SeekFrom::Start(
                header.size + header.track_header_size as u64 + header.name_table_size as u64,
            ))
            .unwrap();
        for idx in 0..header.num_tracks {
            let idx = idx as usize;

            let data_start = tracks[idx].data_offset;
            let mut data_end = data_start + header.data_size;

            if (idx as u32) < header.num_tracks - 1 {
                data_end = tracks[idx + 1].data_offset;
            }

            tracks[idx].data.resize((data_end - data_start) as usize, 0);
            let _ = reader.read(&mut tracks[idx].data).unwrap();
        }

        Ok(Self { header, tracks })
    }
}

pub struct Soundbank {
    pub fsbs: Vec<Fsb5>,
}

impl Soundbank {
    pub fn from_path(filename: &str) -> Self {
        let riff = riff_io::RiffFile::open(filename).unwrap();
        let entries = riff.read_entries().unwrap();
        let mut fsbs = Vec::with_capacity(2);

        for entry in entries {
            match entry {
                Entry::Chunk(meta) => {
                    let fourcc = String::from_utf8_lossy(&meta.chunk_id);
                    if fourcc != "SND " {
                        continue;
                    }

                    let starting_pad = 32 - meta.data_offset % 32;

                    let mut bytes = Cursor::new(riff.read_bytes(
                        meta.data_offset + starting_pad..meta.data_offset + meta.data_size,
                    ));

                    let fsb = Fsb5::from_reader(&mut bytes).unwrap();
                    fsbs.push(fsb);
                }
                Entry::List(_) => {
                    continue;
                }
            }
        }

        Self { fsbs }
    }
}
