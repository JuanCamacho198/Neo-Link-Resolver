/**
 * config.js - Global configuration for Neo-Link-Resolver Extension.
 */

export const QUALITY_PRIORITY = [
    "2160p",  // 4K
    "1080p",  // Full HD
    "720p",   // HD
    "480p",   // SD
    "360p"    // Low
];

export const FORMAT_PRIORITY = [
    "WEB-DL",
    "BluRay",
    "BRRip",
    "HDRip",
    "DVDRip",
    "CAMRip",
    "TS"
];

export const PROVIDER_PRIORITY = [
    "utorrent",      
    "drive.google",  
    "mega",          
    "mediafire",     
    "1fichier",      
    "uptobox",       
    "other"         
];

export class SearchCriteria {
    constructor({ quality = "1080p", format = "WEB-DL", providers = ["utorrent", "drive.google"], language = "latino" } = {}) {
        this.quality = quality;
        this.format = format;
        this.preferredProviders = providers;
        this.language = language;
    }

    matchesQuality(text) {
        if (!this.quality) return true;
        return text.toLowerCase().includes(this.quality.toLowerCase());
    }

    matchesFormat(text) {
        if (!this.format) return true;
        return text.toLowerCase().includes(this.format.toLowerCase());
    }

    matchesLanguage(text) {
        const langMap = {
            "latino": ["latino", "lat", "español latino"],
            "español": ["español", "castellano", "esp"],
            "english": ["english", "inglés", "sub", "subtitulado"]
        };
        const keywords = langMap[this.language] || [this.language];
        return keywords.some(k => text.toLowerCase().includes(k));
    }

    scoreProvider(provider) {
        if (!this.preferredProviders.includes(provider)) return 0;
        const index = this.preferredProviders.indexOf(provider);
        return Math.max(0, 100 - (index * 10));
    }
}
