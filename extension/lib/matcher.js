/**
 * matcher.js - Link ranking engine.
 */

import { QUALITY_PRIORITY, FORMAT_PRIORITY, PROVIDER_PRIORITY } from './config.js';

export class LinkOption {
    constructor({ url, text, provider, quality = "", format = "", score = 0 }) {
        this.url = url;
        this.text = text;
        this.provider = provider;
        this.quality = quality;
        this.format = format;
        this.score = score;
    }
}

export class LinkMatcher {
    constructor(criteria) {
        this.criteria = criteria;
    }

    parseLink(url, text) {
        const textLower = text.toLowerCase();
        const urlLower = url.toLowerCase();
        const combined = `${textLower} ${urlLower}`;

        // Detect provider
        let provider = "other";
        for (const p of PROVIDER_PRIORITY) {
            if (urlLower.includes(p)) {
                provider = p;
                break;
            }
        }

        // Detect quality
        let quality = "";
        for (const q of QUALITY_PRIORITY) {
            if (combined.includes(q.toLowerCase())) {
                quality = q;
                break;
            }
        }

        // Detect format
        let format = "";
        for (const f of FORMAT_PRIORITY) {
            if (combined.includes(f.toLowerCase())) {
                format = f;
                break;
            }
        }

        return new LinkOption({
            url,
            text,
            provider,
            quality,
            format
        });
    }

    scoreLink(link) {
        let score = 0;

        // +40 pts: Exact quality match
        if (this.criteria.quality && link.quality) {
            if (this.criteria.quality.toLowerCase() === link.quality.toLowerCase()) {
                score += 40;
            } else {
                score -= 10;
            }
        }

        // +30 pts: Exact format match
        if (this.criteria.format && link.format) {
            if (this.criteria.format.toLowerCase() === link.format.toLowerCase()) {
                score += 30;
            } else {
                score -= 5;
            }
        }

        // +30 pts: Provider preference
        const providerScore = this.criteria.scoreProvider(link.provider);
        score += (providerScore / 100) * 30;

        // Bonus: language match
        if (this.criteria.matchesLanguage(link.text)) {
            score += 10;
        }

        link.score = Math.max(0, score);
        return link.score;
    }
}
