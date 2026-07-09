export interface GeneralSettings {
  enableLooseFileWarning: boolean;
  disableAssetCaching: boolean;
  speedrunMode: boolean;
  blockSaveGame: boolean;
  allowSaveGameMods: boolean;
  disableSteamAchievements: boolean;
  usePlaylunkySave: boolean;
}

export interface ScriptSettings {
  enableDeveloperMode: boolean;
  enableDeveloperConsole: boolean;
  consoleHistorySize: number;
}

export interface AudioSettings {
  enableLooseAudioFiles: boolean;
  cacheDecodedAudioFiles: boolean;
  synchronousUpdate: boolean;
}

export interface SpriteSettings {
  randomCharacterSelect: boolean;
  linkRelatedFiles: boolean;
  generateCharacterJournalStickers: boolean;
  generateCharacterJournalEntries: boolean;
  generateStickerPixelArt: boolean;
  enableSpriteHotLoading: boolean;
  spriteHotLoadDelay: number;
  enableCustomizableSheets: boolean;
  enableLuminanceScaling: boolean;
}

export interface PlaylunkyOptions {
  general: GeneralSettings;
  script: ScriptSettings;
  audio: AudioSettings;
  sprite: SpriteSettings;
}
