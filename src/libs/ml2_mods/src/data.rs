use serde::{Deserialize, Serialize};

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
    pub logo: String,
    pub mod_file: ManifestModFile,
}
