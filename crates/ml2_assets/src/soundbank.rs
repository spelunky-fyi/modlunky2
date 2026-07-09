use std::io::Cursor;

use riff_io::Entry;
use thiserror::Error;

use crate::fsb5::{Fsb5, Fsb5Error};

#[derive(Error, Debug)]
pub enum SoundbankError {
    #[error("Not FSB5 Data.")]
    Fsb5Error(#[from] Fsb5Error),

    #[error("IoError")]
    IoError(#[from] std::io::Error),
}

pub struct Soundbank {
    pub fsbs: Vec<Fsb5>,
}

impl Soundbank {
    pub fn from_path(filename: &str) -> Result<Self, SoundbankError> {
        let riff = riff_io::RiffFile::open(filename)?;
        let mmap = riff.bytes();
        // riff-io 0.2 returns the outer RIFF as an Entry::List; the SND
        // chunks we care about are its top-level children.
        let root = riff.read_file()?;
        let children = match root {
            Entry::List(list) => list.children,
            Entry::Chunk(_) => return Ok(Self { fsbs: Vec::new() }),
        };

        let mut fsbs = Vec::with_capacity(2);
        for entry in children {
            let Entry::Chunk(chunk) = entry else {
                continue;
            };
            if &chunk.id != b"SND " {
                continue;
            }

            // Soundbank pads each SND chunk's data up to a 32-byte
            // boundary before the FSB5 payload starts; skip the pad so
            // Fsb5::from_reader sees its magic bytes at offset 0.
            let data_offset = chunk.data.offset;
            let data_end = data_offset + chunk.chunk_size;
            let starting_pad = 32 - data_offset % 32;

            let mut bytes = Cursor::new(&mmap[data_offset + starting_pad..data_end]);
            let fsb = Fsb5::from_reader(&mut bytes)?;
            fsbs.push(fsb);
        }

        Ok(Self { fsbs })
    }
}
