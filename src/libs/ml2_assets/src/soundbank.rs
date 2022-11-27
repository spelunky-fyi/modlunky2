use std::io::Cursor;

use riff_io::Entry;
use thiserror::Error;

use crate::fsb5::{Fsb5, Fsb5Error};

pub struct Soundbank {
    pub fsbs: Vec<Fsb5>,
}

#[derive(Error, Debug)]
pub enum SoundbankError {
    #[error("Not FSB5 Data.")]
    Fsb5Error(#[from] Fsb5Error),

    #[error("IoError")]
    IoError(#[from] std::io::Error),
}

impl Soundbank {
    pub fn from_path(filename: &str) -> Result<Self, SoundbankError> {
        let riff = riff_io::RiffFile::open(filename)?;
        let entries = riff.read_entries()?;
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

                    let fsb = Fsb5::from_reader(&mut bytes)?;
                    fsbs.push(fsb);
                }
                Entry::List(_) => {
                    continue;
                }
            }
        }

        Ok(Self { fsbs })
    }
}
