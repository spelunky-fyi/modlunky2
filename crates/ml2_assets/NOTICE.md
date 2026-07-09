# Credits

The Spelunky 2 asset extract + repack pipeline in this crate builds
on reverse-engineering work by several people. Preserved here because
the crate would not exist without them.

- **SciresM** did the original work of extracting these assets.
  https://gist.github.com/SciresM/d97e21a02d4a4cdc11b2b97cf43efea3

- **Cloppershy** cleaned up and expanded SciresM's work, and
  contributed the original implementation of repacking.
  https://gist.github.com/Cloppershy/a32b9139f3d222b5ff5b8b23ffac1aac
  https://gist.github.com/Cloppershy/046846e593362a2a7284c28f39899eae

  Cloppershy also identified the alignment issue that prevented
  audio from working after repacking.

- **iojonmbnmb#8149** provided the updated hashing code when it was
  changed in Spelunky 2 version 1.13.0.
