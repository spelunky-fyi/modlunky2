use std::io::{BufRead, Write};

use crc32fast::Hasher;

pub struct StringHasher {
    pub hashes: Vec<Option<String>>,
}

impl StringHasher {
    pub fn from_reader<R: BufRead>(reader: R) -> Self {
        let mut hashes = Vec::with_capacity(2600);
        let mut current_section: Option<String> = None;

        let comment_matches = &[' ', '#'];

        for line in reader.lines() {
            let line: String = match line {
                Ok(line) => line.trim().into(),
                Err(_) => continue,
            };

            let mut string_hash: Option<String> = None;
            if line.starts_with('#') {
                let comment_section = line.trim_matches(&comment_matches[..]);
                if !comment_section.is_empty() {
                    current_section = Some(comment_section.into());
                }
            } else {
                let mut to_hash: String = line;
                if let Some(current_section) = &current_section {
                    to_hash.push_str(current_section);
                }

                let mut hasher = Hasher::new();
                hasher.update(to_hash.as_bytes());
                let checksum = hasher.finalize();

                string_hash = Some(format!("0x{:08x}", checksum));
            }

            hashes.push(string_hash);
        }

        Self { hashes }
    }

    pub fn merge_hashes<W: Write>(
        &self,
        lines: &Vec<String>,
        writer: &mut W,
    ) -> Result<(), std::io::Error> {
        assert!(lines.len() == self.hashes.len());

        for (line_num, line) in lines.iter().enumerate() {
            let hash = &self.hashes[line_num];

            if let Some(hash) = hash {
                writer.write(format!("{}: {}\n", &hash, line).as_bytes())?;
            } else {
                writer.write(format!("{}\n", line).as_bytes())?;
            }
        }
        Ok(())
    }
}
