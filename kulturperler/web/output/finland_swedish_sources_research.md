# Research: Finnish Sources for Swedish-Language Performing Arts Content

**Focus:** Finland-Swedish (finlandssvensk) content only - Swedish-language productions from Finland's Swedish-speaking minority (~5%)

**Research Date:** December 27, 2025
**Location:** Norway (accessibility tested from Norwegian IP)

---

## 1. Yle (Finnish Broadcasting Company)

### Overview
- Finland's national public broadcasting company
- Provides Swedish-language programming through **Svenska Yle**
- ~5.5% of Finland's population speaks Swedish as their native language

### Swedish-Language Channels

#### Yle Teema & Fem (TV)
- **Description:** Combined culture/education channel
- **Content:** Recordings of performing arts, classical music, news, documentaries, children's programming
- **Language:** Swedish with Finnish subtitles
- **History:** Previously separate as "Yle Fem" (launched 2001 as YLE FST, relaunched 1988)
- **Focus areas:** Culture, education, science, performing arts recordings, classical music

#### Yle Vega (Radio)
- **Description:** Swedish-language radio channel
- **Content:** News, current affairs, culture, music (classical, jazz, pop, folk)
- **Target audience:** Mature audiences
- **Launched:** 1997 (replaced Riksradion from 1961)
- **Music emphasis:** Finland-Swedish music specifically

#### Yle X3M (Radio)
- **Description:** Youth-oriented Swedish-language channel
- **Content:** Current affairs, popular culture, news, new pop and rock music

### Yle Arenan - Streaming Service

**URL:** https://arenan.yle.fi

**Accessibility from Norway:** ✅ **ACCESSIBLE** (tested successfully)

**Content Categories Visible:**
- Svenska Yle Originals (Swedish-language originals)
- Nordiska dramaserier (Nordic drama series)
- Internationella dramaserier (International drama series)
- Dokumentärer (Documentaries)
- Krim och spänning (Crime and thriller)
- Livsstil (Lifestyle)

**Navigation:**
- TV section: https://arenan.yle.fi/tv
- Poddar (Podcasts): https://arenan.yle.fi/poddar
- Direkt (Live): https://arenan.yle.fi/direkt
- Can stream Yle Vega live and archived content
- Interface available in Swedish and Finnish

**Note on Theater/Radio Drama:**
- No dedicated "Teater" or "Radioteater" section visible in main navigation
- Content may be under "Kultur" category or searchable via the site search
- Historical radio drama (radioteater) archives not prominently displayed

### Yle API

**Documentation:** https://developer.yle.fi/en/index.html

**Status:** Experimental (opened May 2015)

**Currently Available APIs:**
- ❌ **Teletext only** - Currently the only public API available
- ❌ No access to program metadata, radio drama, theatre productions, or cultural programs
- ❌ No dedicated programs/content endpoints for Swedish-language content

**Access Requirements:**
- Register for Yle Tunnus account
- Request API keys at developer.yle.fi
- Rate limits: 10 requests/second, 300 requests/hour, 7200 requests/day

**Technical Details:**
- Base URL: https://external.api.yle.fi
- Test environment: https://external.api-test.yle.fi
- Response format: JSON (default)
- Authentication: app_id + app_key per request
- Supports gzip compression

**Verdict:** ❌ Not useful for discovering Swedish-language performing arts content

### Geographic Restrictions
- ✅ **No geoblocking detected from Norway**
- Yle Arenan accessible and functional from Norwegian IP
- EU geo-blocking regulation applies (Norway is included)

---

## 2. Finnish Swedish-Language Theatres

### Svenska Teatern (Helsinki)

**Overview:**
- Finland's first national stage
- Finnish national theatre performing in Swedish
- Founded 1866, current building renovated 1935 (Eero Saarinen & Jarl Eklund)

**Location:** Erottaja (Skillnaden) square, Helsinki
**Website:** https://svenskateatern.fi/en/

**Stages:**
- Stora Scenen (Main Stage): 600 seats
- AMOS: ~160 seats
- NICKEN: ~90 seats

**Productions:** 8-10 pieces annually (in-house + collaborations)

**Subtitles:** Most performances surtitled in Finnish, Swedish, and occasionally English

**Digital Presence:**
- ❌ No YouTube channel found
- ✅ Instagram: @svenskateatern (8,555 followers)
- ❌ No digital archive or recordings visible

**Historical Note:** Jean Sibelius premiered early version of Finlandia here

### Åbo Svenska Teater (Turku/Åbo)

**Overview:**
- Finland's oldest theatre (founded 1839)
- Oldest still-functioning theatre building in Finland
- Swedish-speaking theatre in Turku

**Website:** https://abosvenskateater.fi/en/

**Stages:**
- Stora Scenen (Main Stage): 365 seats
- Plus two smaller stages

**Subtitles:** All Main Stage performances subtitled in Swedish and Finnish

**Ownership:** Stiftelsen för Åbo Akademi (managed by Åbo Svenska Teaterförening)

**Digital Presence:**
- ❌ No YouTube channel found
- ✅ Instagram: @abosvenskateater
- ❌ No digital recordings or streaming visible

### Wasa Teater (Vaasa)

**Overview:**
- Regional theatre of Österbotten
- Founded 1919 (100+ years of history)
- Professional Swedish-language theatre

**Website:** https://www.wasateater.fi/en/

**Building:** Renovated 2019 with state-of-the-art stage technology (first Nordic theatre with next-generation sound system)

**Stages:**
- Large stage: 272 seats
- Studio: 80-120 seats
- Vasallen: 62 seats

**Digital Presence:**
- ❌ No YouTube channel found
- ✅ Instagram: @wasateater (5,339 followers)
- ❌ No digital archive visible

### Klockriketeatern (Helsinki)

**Description:** Finland-Swedish nomadic theatre ("the world is our stage")
**Status:** State-subsidized theater (statsandelsteater) since 2022
**Website:** https://klockrike.fi/sv/teatern/

### Teater Magnitude

**Description:** Finland-Swedish theater group for people with functional variations
**Mission:** "Theater for all"

### Digital Recordings Summary

**Theatre Recordings:** ❌ None of the major Finland-Swedish theatres appear to have:
- Dedicated YouTube channels
- Publicly accessible digital archives
- Streaming recordings of performances
- Online video content

**Social Media:** ✅ All have Instagram presence, but no video archives

---

## 3. National Library of Finland (Kansalliskirjasto)

### Digitized Collections

**Main Portal:** https://digi.kansalliskirjasto.fi/etusivu?set_language=en

**Accessibility:** Requires JavaScript - full interface not accessible via simple fetch

### Swedish-Language Newspaper Digitization

**Project Completed:** 2023 (3-year project)

**Content:**
- Almost 6 million pages of Swedish-language newspapers digitized
- Coverage: Finnish Swedish-language newspapers up to end of 1940s
- Public access: Freely available until December 31, 1949
- More recent materials: Available at legal deposit libraries

**Access Points:**
- digi.kansalliskirjasto.fi (public)
- Svenska Litteratursällskapet archives (Helsinki and Vaasa)
- Brages Pressarkiv (Mariehamn)
- Ålands landskapsarkiv (Mariehamn)

**Funding:** 1.85 million euros from eight funds and foundations

### Web Archive (Verkkoarkisto)

**URL:** https://verkkoarkisto.kansalliskirjasto.fi/va/

**Content:**
- Finnish Web Archive launched 2006
- Size: Over 300 TB (2025)
- Annual preservation: ~20 TB
- Includes Swedish dialects in Finland materials

**Access:** ❌ Only viewable at legal deposit workstations ("vapaakappaleasemilla")

**Potential Content:**
- One reference found to "Vaasa Wasa teater 1969-1971" collection in Finna.fi
- May contain archived Swedish-language broadcasts from Svenska Yle
- Cannot be verified without physical access to legal deposit terminals

### Audio Collections

**Listening Room:** Available at National Library with old Finnish recordings

**Swedish-Language Broadcasts:** ❌ No specific information found about digitized Swedish-language radio/TV theatre broadcasts

**Search Portal:** https://www.finna.fi (includes National Library collections)

**Theatre Programme Collection:** Exists but focus is on printed programmes, not recordings

---

## 4. Svenska Litteratursällskapet i Finland (SLS)

### Overview

**Full Name:** Society of Swedish Literature in Finland (Svenska litteratursällskapet i Finland r.f.)

**Website:** https://www.sls.fi/en/

**Mission:** Scholarly society for collection, archiving and dissemination of knowledge about Finland-Swedish culture

### Archive Collections

**Content Types:**
- Personal and family archives
- Manor archives
- **Theatre archives** ✅
- Community archives
- Folk culture records
- Dialect recordings
- Folk music and dance recordings
- Photographs
- Oral traditions (fairy tales, proverbs, legends)

### Digital Resources

#### Talko - Spoken Language Corpus
- Recordings from 2005-2008 ("Save the Finland-Swedish speech" project)
- Searchable transcripts with word-class tags
- Available on Finna search service

#### Finlands svenska folkdiktning
- 12,000+ pages of folk traditions (tales, legends, proverbs, riddles)
- 3,000+ melodies to listen to and download
- Focus: 19th/early 20th century materials

#### Finland-Swedish Folk Music Institute (FMI)
- Works with folk music and dance in Swedish in Finland
- Collections searchable at sls.finna.fi

### Search Portal

**URL:** https://sls.finna.fi

**Content Searchable:**
- Archival materials
- Recordings ✅
- Images
- Manuscripts
- Music collections
- Library holdings
- Sound archive collections

**Access:** Free use for published online materials

### Theatre Archives

**Status:** ✅ Theatre archives mentioned as part of collections

**Specifics:** Not detailed in search results - would need to contact SLS directly or search at sls.finna.fi

**Collaboration:** SLS has cooperated with Svenska Yle - some Yle material deposited in SLS archives

---

## 5. Additional Resources

### Historical Radio Materials Abroad

Some Finnish radio heritage is located abroad:
- Swedish National Library's audio-visual collections
- DokuFunk (international radio documentation centre, Austria)

### Ålands Radio

- Formerly part of Yleisradio until 1996
- Now independent
- Historical holdings: Ålands landskapsarkiv (provincial archives)

---

## Summary & Recommendations

### ✅ Accessible & Promising

1. **Yle Arenan** (https://arenan.yle.fi)
   - **Accessible from Norway:** Yes
   - **Swedish content:** Yes (Svenska Yle section)
   - **Performing arts:** Likely present but requires manual search/browsing
   - **Recommendation:** Manually explore "Kultur" section and search for "teater", "radioteater", "opera"

2. **SLS Archives** (https://sls.finna.fi)
   - **Theatre archives:** Yes (confirmed in collections)
   - **Audio recordings:** Yes
   - **Access:** Online materials free to use
   - **Recommendation:** Search for Swedish theatre recordings and Yle collaborations

3. **National Library Digital Collections** (https://digi.kansalliskirjasto.fi)
   - **Swedish newspapers:** 6 million pages digitized (up to 1949)
   - **Web archive:** May contain Yle content but requires physical access
   - **Recommendation:** Useful for research context but not for video/audio content

### ❌ Limited or No Digital Access

1. **Swedish-Language Theatres**
   - Svenska Teatern, Åbo Svenska Teater, Wasa Teater
   - **YouTube channels:** None found
   - **Digital archives:** None publicly accessible
   - **Recommendation:** Contact theatres directly for any archive projects

2. **Yle API**
   - **Current status:** Teletext only
   - **Content APIs:** Not available
   - **Recommendation:** Not useful for content discovery

### 🔍 Requires Further Investigation

1. **Yle Arenan Manual Search**
   - Search terms to try: "radioteater", "teater", "opera", "konsert", "kulturprogram"
   - Browse "Kultur" and "Dokumentärer" sections
   - Check podcast section for radio drama archives

2. **SLS Theatre Archives**
   - Contact SLS directly about Swedish theatre recordings
   - Inquire about Yle material deposited in their archives
   - Search sls.finna.fi for "teater", "Yle", "radioteater"

3. **Finna.fi National Search**
   - Search across all Finnish cultural institutions
   - May reveal Swedish-language performing arts content across multiple archives

### Key Contacts for Follow-Up

- **Svenska Yle:** Contact via svenska.yle.fi for radio drama archives
- **SLS Archives:** https://www.sls.fi/en/sls-customer-service
- **National Library of Finland:** For Web Archive access inquiries
- **Individual Theatres:** For any unpublicized digital archive projects

### Geographic Accessibility

✅ **Good news for Norway:** No geoblocking detected for:
- Yle Arenan streaming
- SLS digital collections
- National Library digital newspapers

---

## Comparison with NRK

| Feature | NRK (Norway) | Yle/Svenska Yle (Finland) |
|---------|--------------|----------------------------|
| **Geographic access from Norway** | Native | ✅ Accessible |
| **Public API** | ✅ Yes (psapi.nrk.no) | ❌ No (teletext only) |
| **Streaming platform** | ✅ NRK TV | ✅ Yle Arenan |
| **Swedish-lang theatre recordings** | N/A | Unknown (requires manual search) |
| **Radio drama archives** | ✅ Extensive | Unknown (not prominently featured) |
| **Metadata accessibility** | ✅ Excellent via API | ❌ Manual only |

### Key Differences

1. **API Access:** NRK has rich API; Yle does not (major limitation)
2. **Language Context:** NRK is Norwegian-only; Yle serves both Finnish and Swedish (minority)
3. **Archive Prominence:** NRK showcases archives; Yle Arenan focuses on recent content
4. **Theatre Recordings:** NRK has extensive Fjernsynsteatret; Yle's theatre content unclear

---

## Next Steps for Kulturperler Integration

### High Priority

1. **Manual exploration of Yle Arenan**
   - Search for Swedish-language theatre and radio drama
   - Document any series or collections found
   - Note PRF IDs / program IDs for potential import

2. **Contact Svenska Yle directly**
   - Inquire about radio drama (radioteater) archives
   - Ask about theatre recordings availability
   - Request information about metadata access

3. **Search SLS archives at sls.finna.fi**
   - Look for theatre recordings
   - Check for Yle deposited materials
   - Identify any Finland-Swedish performing arts audio

### Medium Priority

4. **Check Finna.fi national portal**
   - Search across all Finnish institutions
   - Look for Swedish-language performing arts content

5. **YouTube manual search**
   - Search directly: "Svenska Teatern", "Åbo Svenska Teater", "finlandssvensk teater"
   - Check for unofficial uploads or clips

### Low Priority

6. **Contact individual theatres**
   - Inquire about digital archive projects
   - Ask if any recordings exist (even if not public)

---

## Technical Notes for Implementation

### If Content is Found on Yle Arenan

**Challenges:**
- ❌ No API - would require web scraping
- ❌ Dynamic React/Next.js application (harder to scrape)
- ❌ May have DRM/playback restrictions
- ✅ Geographic access works from Norway

**Potential Approach:**
- Use browser automation (Playwright/Puppeteer) to search
- Extract program metadata from page content
- Store program IDs for manual reference
- Link to Yle Arenan URLs (no direct video embedding likely)

### If Using SLS Archives

**Metadata:**
- Check if sls.finna.fi has API or structured data export
- Finna uses standard library metadata formats
- May have IIIF support for digital objects

**Integration:**
- Similar to National Library of Finland newspaper integration
- Focus on audio recordings and theatre materials
- Link to Finna search results or individual items

---

## Conclusion

Finland offers Swedish-language performing arts content through **Yle Arenan** (accessible from Norway) and archives like **SLS** and the **National Library**. However:

- **No programmatic access** via APIs (unlike NRK)
- **Theatre recordings** from Swedish-language theatres are not publicly available online
- **Radio drama archives** exist but are not prominently featured
- **Manual research required** to identify specific Swedish-language performing arts content

**Best opportunity:** Manually exploring Yle Arenan's Swedish content and contacting Svenska Yle directly about their radioteater archives.

**Comparison to NRK:** Finland's infrastructure for accessing Swedish-language performing arts content is significantly less developed than NRK's Norwegian content accessibility, primarily due to lack of API access and less prominent archival presentation.
