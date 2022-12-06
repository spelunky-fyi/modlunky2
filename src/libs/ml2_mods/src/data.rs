use serde::{Deserialize, Serialize};

use crate::manager::Error;

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct Mod {
    pub id: String,
    pub manifest: Option<Manifest>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ManifestModFile {
    pub id: String,
    pub created_at: String,
    pub download_url: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct Manifest {
    pub name: String,
    pub slug: String,
    pub description: String,
    pub logo: Option<String>,
    pub mod_file: ManifestModFile,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum DownloadProgress {
    Waiting(),
    Started(),
    Receiving {
        expected_bytes: Option<u64>,
        received_bytes: u64,
    },
    Finished(),
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ModProgress {
    Waiting {
        id: String,
    },
    Started {
        id: String,
    },
    Downloading {
        id: String,
        main_file: DownloadProgress,
        logo_file: DownloadProgress,
    },
    Finished {
        r#mod: Mod,
    },
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum Change {
    Add { progress: ModProgress },
    Remove { id: String },
    Update { progress: ModProgress },
    NewVersion { id: String },
}

#[derive(Debug, Serialize, Deserialize, thiserror::Error)]
pub enum ManagerError {
    #[error("{0}")]
    ModExistsError(String),
    #[error("{0}")]
    ModNotFoundError(String),
    #[error("{0}")]
    ModNonDirectoryError(String),
    #[error("{0}")]
    ManifestParseError(String),
    #[error("{0}")]
    SourceError(String),
    #[error("{0}")]
    DestinationError(String),
    #[error("{0}")]
    ChannelError(String),
    #[error("{0}")]
    UnknownError(String),
}

impl From<Error> for ManagerError {
    fn from(original: Error) -> Self {
        match original {
            Error::ModExistsError(_) => ManagerError::ModExistsError(format!("{original}")),
            Error::ModNotFoundError(_) => ManagerError::ModNotFoundError(format!("{original}")),
            Error::ModNonDirectoryError(_) => {
                ManagerError::ModNonDirectoryError(format!("{original}"))
            }
            Error::ManifestParseError(_) => ManagerError::ManifestParseError(format!("{original}")),
            Error::SourceError(_) => ManagerError::SourceError(format!("{original}")),
            Error::DestinationError(_) => ManagerError::DestinationError(format!("{original}")),
            Error::ChannelError(_) => ManagerError::ChannelError(format!("{original}")),
            Error::UnknownError(_) => ManagerError::UnknownError(format!("{original}")),
        }
    }
}
