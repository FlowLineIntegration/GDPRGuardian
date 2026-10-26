# ids-france

### Key takeaways
- Strong checksums exist only for: NIR/NIA (97 - N mod 97), numéro fiscal SPI (first 10 digits mod 511), TVA FR (mod 97, or mod 11 for alphanumeric keys), IBAN (mod 97) plus clé RIB, and MRZ lines (ICAO 7-3-1). On these, a validated match is safe to redact without context.
- Luhn-only identifiers are SIREN, SIRET, RPPS, FINESS, and probably ADELI. About 10% of random numbers pass Luhn, so a match alone is too weak: require context words or a column header.
- No checksum (detect from context only): old and new CNI numbers, passport, permis NEPH, AGDREF numéro étranger, RNA, NUMEN, CAF allocataire, France Travail ID, accise, plates, phones, postal codes, addresses, and patient, contract and customer numbers.
- As of 2026-10-24, Presidio has no French recognizers. It moved to data-privacy-stack/presidio (MIT, v2.2.364). The FR_NIR PR #2314, SIREN/SIRET #2320/#2321 and RPPS/FINESS #2342 are open and unmerged. GDPR Guardian must implement France itself, ideally reusing those entity names.
- python-stdnum 2.2 (LGPL-2.1+) covers fr.nir, nif, siren, siret (La Poste exception), tva (alphanumeric keys), rcs and accise. django-localflavor (BSD-3) covers NIR, SIREN, SIRET, RNA and zip codes. Faker (MIT) generates valid NIR, SIREN and SIRET but invalid TVA and RIB keys.
- NIR edge cases: Corsica 2A/2B (count them as 19/18 when computing the key; dept 20 before 1976), 99 plus a country code for births abroad, 3-digit DOM dept with a 2-digit commune, sex 3/4/7/8 for people being registered or temporary numbers, fictitious months 20-42 and 50-99. localflavor rejects sex 3/4, and stdnum does not check sex or month.
- The MRZ (2x36 old CNI, 3x30 CNIe, 2x44 passport) encodes document number, name, date of birth, sex and expiry. Its check digits make it low-FP. Redact the whole MRZ block after Markdown conversion or OCR.
- French typography and Office exports use NBSP (U+00A0) and narrow NBSP (U+202F) as digit-group separators. Every separator class must include them along with space, dot and hyphen.
- DOM-TOM: NIR dept 971-976 (98x for TOM births); phones +590/+594/+596/+262 with 9 digits, +508/+681/+687 with 6 digits, +689 with 8 digits; postal codes 971xx-976xx, 97133/97150, 986-988xx; FINESS uses prefix 97 (territory in 4th char) and 98 for Mayotte; FNI plates 971-976. Mayotte and Guyane addresses often have no street number.
- Excel (the user's question): process it, cell by cell, with header-aware rules. Context comes from column headers. Check what share of a column's cells pass the validator, then label the whole column. Watch for coercion: postal and phone codes lose leading zeros, the NIR is often split from its key, NIR shows in scientific notation, and dates are stored as serial numbers.
- SIREN and SIRET identify a natural person only for entrepreneurs individuels and micro-entrepreneurs. Make redaction of company identifiers a policy setting, not a fixed default.
- The shared WebSearch budget (200 calls) ran out during this research. Formats for France Travail, CAF, passport, the permis front-card number, the NIA key and the ADELI/AM keys rely on secondary or no sources and are flagged unverified.

### Recommendations
- Use three confidence tiers. (1) Strong checksum (NIR, SPI, TVA, IBAN/RIB, MRZ): redact on a validated match. (2) Luhn-only (SIREN, SIRET, RPPS, FINESS): require a context word within about 5 tokens or a matching column header. (3) No checksum (CNI, passport, NEPH, AGDREF, CAF, France Travail, NUMEN, plates, postal codes): context only.
- Normalize before matching: NFKC, map U+00A0/U+202F/U+2009 to space, and use one separator class [ .\-  ]. Use digit-boundary lookarounds instead of \b so 'n°123' and '2A' work. Prefilter with one combined regex (or the regex module or Hyperscan) and run validators only on candidates.
- NIR: accept sex [1-478], any 2-digit month, and dept 2A/2B (also lowercase); let the mod-97 key decide. Optionally lower confidence for impossible fields rather than rejecting. Add a 13-digit keyless rule gated on context or column header.
- Implement all validators in MIT code from the specs (algorithms are facts). Keep python-stdnum and django-localflavor as dev-only test oracles; do not copy their source.
- Resolve overlaps: SIRET contains SIREN, TVA/EORI/RCS contain SIREN, IBAN contains the RIB. Keep the longest validated span and type it by the outermost identifier.
- Make company-identifier redaction a policy setting: off for legal persons by default, on when EI or micro-entrepreneur context is present, or in strict mode. Also decide whether health-professional IDs (RPPS, ADELI) are pseudonymized.
- Redact the MRZ as a single block, with OCR-tolerant matching (O/0, «/<, spaces). Validate the 7-3-1 check digits to raise confidence, not to gate.
- Excel: yes, process it. Do not rely only on Markdown conversion. Read cell values plus number formats and header rows. Classify each column by header keywords and the share of cells passing validation (e.g., 80% or more). Pseudonymize the whole column consistently. Re-pad leading zeros for postal codes, phones and SPI. Rejoin NIR with its key when split across adjacent columns. Format date serials as dates before DOB rules run.
- Offer generalization for quasi-identifiers (postal code to dept, DOB to year, commune to dept) besides placeholders, because NIR fields, DOB, sex and postal code allow re-identification when combined.
- Build a synthetic French test corpus with Faker plus custom generators: 2A/2B, DOM 97x, 99 plus country code, sex 3/4/7/8, special months, La Poste SIRET, alphanumeric TVA keys, alphanumeric RIB accounts, DOM phones, NBSP-separated numbers and Excel-coerced numbers.
- Before shipping, confirm the unverified formats (INE RNIE key, ADELI/AM key, CAF, France Travail, passport, permis front number, NIA key) with official sources or real anonymized samples.

### Risks
- False positives from Luhn-only checks: about 1 in 10 random 9- or 14-digit numbers (invoice and order numbers) passes, causing over-redaction that breaks LLM utility unless context is required.
- False negatives on context-only IDs (new CNI 9 alphanumeric chars, NEPH, AGDREF, CAF) in terse text or spreadsheets without headers.
- Wrong or outdated specs: INE, ADELI, France Travail, CAF and passport formats come from community or secondary sources; the search budget ran out before official confirmation.
- LGPL contamination if python-stdnum code is copied into the MIT codebase; an import-only dependency is fine but carries redistribution obligations.
- Excel coercion (lost leading zeros, scientific notation, date serials, NIR split from its key) silently defeats regex and checksum detection.
- OCR'd documents: MRZ and digit misreads break checksums, so strict validation yields false negatives.
- Presidio FR recognizers may merge later with different entity names or semantics, causing divergence if GDPR Guardian does not align early.
- NIR is a GDPR Art. 87 national identification number with a restrictive French framework: any residual leak is high-severity, so it needs recall-oriented settings.

### Open questions
- Official INE specification (RNIE 2-letter mod-97 key, BEA mod-23 key, SIFA and Base 100 variants): only community sources were found.
- ADELI and AM numéro key algorithm (Luhn?) and whether 2A/2B appear in ADELI; ANS says only '9 alphanumeric characters'.
- Exact formats of the CAF allocataire number and the France Travail identifier: not verified because the search budget ran out.
- Does the NIA (SANDIA) use the same mod-97 key as the NIR? Do sex digits 3/4 still occur in practice?
- Character set of the new CNIe 9-character number (excluded letters?) and format of the front-of-card permis document number.
- Is the French EORI always FR + SIRET (14 digits), and what do individuals without a SIRET get?
- Official confirmation that DOM/COM IBANs use the FR prefix (SWIFT IBAN registry not fetched in this session).
- Scope for New Caledonia and French Polynesia, which have their own identifiers (RIDET, numéro TAHITI, CAFAT/CPS numbers) outside French national formats.
- Policy: should SIREN/SIRET of legal persons and health-professional IDs (RPPS/FINESS) be pseudonymized by default?
- Carte grise 'numéro de formule' and electricity PDL/PRM or gas PCE structures: not researched (search budget exhausted).

### Critical claims
- python-stdnum fr.nir computes the NIR key as 97 - (int(first 13 chars) % 97), replacing 2A with 19 and 2B with 18 only for the calculation; it does not validate the sex or month fields. [https://github.com/arthurdejong/python-stdnum/blob/master/stdnum/fr/nir.py]
- The French numéro fiscal (SPI/NIF) is 13 digits with first digit 0-3; its last 3 digits equal int(first 10 digits) mod 511 (python-stdnum fr.nif). [https://github.com/arthurdejong/python-stdnum/blob/master/stdnum/fr/nif.py]
- python-stdnum fr.siret: SIRETs starting with 356000000 (La Poste), except 35600000000048, are valid if the digit sum is a multiple of 5 instead of passing Luhn. [https://github.com/arthurdejong/python-stdnum/blob/master/stdnum/fr/siret.py]
- python-stdnum fr.tva: the numeric key equals int(SIREN + '12') mod 97; alphanumeric keys use an alphabet excluding I and O with a mod-11 check; Monaco numbers (000 at positions 3-5) are valid TVA but not SIREN. [https://github.com/arthurdejong/python-stdnum/blob/master/stdnum/fr/tva.py]
- python-stdnum latest version is 2.2, released 2026-01-04, licensed LGPLv2+; its fr package contains accise, nif, nir, rcs, siren, siret, tva. [https://pypi.org/project/python-stdnum/]
- Presidio main branch (data-privacy-stack/presidio) has no France folder in predefined_recognizers/country_specific; the FR_NIR recognizer PR #2314 is open and unmerged, with no reviews. [https://github.com/data-privacy-stack/presidio/pull/2314]
- presidio-analyzer latest is 2.2.364 (2026-07-22), MIT, with repository at github.com/data-privacy-stack/presidio. [https://pypi.org/project/presidio-analyzer/]
- django-localflavor FRNationalIdentificationNumber accepts only sex digits 1, 2, 7, 8 and months 01-12, 20, 30-42, 50-99; FRRNAField validates ^W\d{9}$. [https://github.com/django/django-localflavor/blob/master/localflavor/fr/forms.py]
- ANS (01/2023): RPPS = 11 non-meaningful digits with a Luhn key; ADELI = 9 alphanumeric chars (dept + profession); FINESS = 9 numeric chars with the first two giving the department. [https://esante.gouv.fr/sites/default/files/media/document/Comprendre_les_differences_entre_les_identifiants_RPPS_ADELI_AM_et_FINESS.pdf]
- The FINESS 9th digit is a Luhn mod 10 key computed on the first 8 digits; Mayotte FINESS numbers start with 98 and DOM numbers with 97. [https://documentation-snds.health-data-hub.fr/snds/fiches/ref_etab]
- The new French CNI (since 2 August 2021) has a 9-character alphanumeric number and a 3x30 MRZ; the old card (1988-2021) has a 12-character number (YYMM + office + sequence) and a 2x36 MRZ. [https://fr.wikipedia.org/wiki/Carte_nationale_d'identité_en_France]
- INS assignment-authority OIDs: INS-NIR 1.2.250.1.213.1.4.8, INS-NIA 1.2.250.1.213.1.4.9, test INS-NIR 1.2.250.1.213.1.4.10, demo 1.2.250.1.213.1.4.11. [https://industriels.esante.gouv.fr/sites/default/files/media/document/asip_referentiel_identifiant_national_sante-liste-des-oid-des-autorites-d-affectation-des-ins_v0.1.pdf]
- SIV plates use 23 letters (no I, O, U), exclude SS and WW in the first block and SS in the second, and 000 is not valid. [https://fr.wikipedia.org/wiki/Plaque_d'immatriculation_française]
- schwifty (MIT) implements the French/Monaco RIB key as 97 - ((89*bank + 15*branch + 3*account) mod 97) with letters A-I/J-R mapped to 1-9 and S-Z to 2-9. [https://github.com/mdomke/schwifty/blob/main/schwifty/checksum/france.py]
- The Base Adresse Nationale dataset is published under Licence Ouverte / Open Licence version 2.0. [https://www.data.gouv.fr/fr/datasets/base-adresse-nationale/]

### Verification ({'confirmed': 28, 'uncertain': 7})
- [uncertain] 9. ANS (01/2023): RPPS = 11 digits with Luhn key; ADELI = 9 alphanumeric chars; FINESS = 9 numeric chars, first two = department.
  - correction: The ANS PDF (and every esante.gouv.fr page tried) returned empty content to WebFetch, so this could not be verified. SNDS shows that FINESS is '9 caractères' and that Corsican FINESS numbers start with 2A/2B, so 'numeric' is imprecise.
  - src: https://esante.gouv.fr/sites/default/files/media/document/Comprendre_les_differences_entre_les_identifiants_RPPS_ADELI_AM_et_FINESS.pdf
- [uncertain] 22. FR_INS: matricule INS = NIR or NIA (NIA assigned by CNAV/SANDIA); CPAM temporary numbers start with 7/8; OIDs .4.8/.4.9/.4.10/.4.11; same mod-97 key assumed for the NIA.
  - correction: The OIDs are confirmed. FR Core describes INS-NIA only as the temporary identifier obtained through the CNAM INSi teleservice. The SANDIA/CNAV assignment, the NIA's format and its key were not verifiable because the ANS PDFs were unreadable.
  - src: https://hl7.fr/ig/fhir/core/StructureDefinition-fr-core-patient-ins.html
- [uncertain] 29. FR_EORI: country code + up to 15 alphanumerics; France normally FR + SIRET (unverified).
  - correction: The EU structure (2-letter country code + up to 15 alphanumerics) is confirmed by the Commission. The FR + SIRET rule could not be checked: the douane.gouv.fr URLs tried returned 404.
  - src: https://taxation-customs.ec.europa.eu/customs-4/customs-procedures-import-and-export-0/customs-procedures/economic-operators-registration-and-identification-number-eori_en
- [uncertain] 31. FR_RPPS: 11 digits with Luhn key (e.g., 10000812437); '8' prefix in identifiant national PS unverified.
  - correction: The example 10000812437 does pass Luhn (digit sum 30), but no ANS source could be read to confirm the Luhn rule. FR Core says the IDNPS 'ne doit être ni construit ni interprété' and lists source prefixes 1,3,4,5,6 (system urn:oid:1.2.250.1.71.4.2.1). The '8'+RPPS construction is still unconfirmed.
  - src: https://hl7.fr/ig/fhir/core/StructureDefinition-fr-core-practitioner.html
- [uncertain] 32. FR_ADELI: 9 chars dept+profession+sequence+key; no longer used since Oct 2024 per ANS; AM 9 digits; key reportedly Luhn.
  - correction: The esante.gouv.fr pages and PDFs returned empty content, so the October 2024 end date and the key algorithm are unverified.
  - src: 
- [uncertain] 34. FR_INE variants and community-sourced checksums (RNIE mod 97 to 2 letters, BEA mod 23, higher-ed base-36 mod 10).
  - correction: No official specification was found or checked, and the WebSearch budget was already used up.
  - src: 
- [uncertain] 35. FR_CARTE_VITALE: card carries the NIR; serial has no public format; NIR mod-97 key.
  - correction: 
  - src: 
### Verifier notes
- Presidio numbering error: #2320 and #2342 are issues (feature requests), not PRs. The only SIREN/SIRET PR is #2321 (open, opened 2026-09-30). #2342 (FR_RPPS/FR_FINESS) is an open issue opened 2026-10-10. PR #2314 (FR_NIR) sets enabled: false by default. Entity names to reuse: FR_NIR, FR_SIREN, FR_SIRET, FR_RPPS, FR_FINESS.
- NIR months: Wikipedia also lists month 13 (some unknown birth months). Fictitious months are 20-30 and 50+, pseudo-fictitious months are 31-42. localflavor accepts only 20 and 30-42, so it also rejects 13 and 21-29, not just sex 3/4. The recommendation to accept any 2-digit month and let the key decide is right. Cite INSEE's xml.insee.fr/schema/nir.html as the primary source for the key (A/B->0 then subtract 1,000,000/2,000,000); it lists only sex 1/2 officially.
- FINESS Corsica: SNDS gives its own substitution (2A -> '2001xxxx', 2B -> '2002xxxx'), distinct from the NIR's 19/18. Do not reuse the NIR rule; implement and test the SNDS rule. FINESS can contain letters (2A/2B), so the claim that it is all-numeric is wrong.
- The 'strong checksum' tier is overstated in two places. (a) Each MRZ check digit is only mod 10; the low false-positive rate comes from the fixed layout (IDFRA, P<FRA, '<' fillers) and the several check digits together. The old CNI MRZ has no expiry field. (b) Alphanumeric-key TVA checks are mod 11 (about 1/11) plus the SIREN Luhn (about 1/110 combined), much weaker than numeric keys (about 1/970). Rely on the 'FR' prefix there.
- Old CNI cards (12-character number, 2x36 MRZ) remain valid for years. Adult cards issued 2014-2021 are valid 15 years, so up to about 2036. The detector must keep both formats.
- SIV plates: WW is excluded only from regular series. WW-xxx-XX temporary plates exist (pink background with an expiry date from 2026) and identify a vehicle, so the plate regex must accept WW in the first block.
- Postal codes: Monaco (980xx, e.g. 98000) is missing from the DOM-TOM list. It uses the French postal system.
- Normalization: NFKC already maps U+00A0, U+202F and U+2009 to U+0020, so the explicit mapping is redundant. NFKC also changes string length (ligatures, the ellipsis character, fractions) and turns superscript and fullwidth digits into ASCII digits. Keep an offset map back to the original text, or apply only a 1:1 character mapping for separators, otherwise redaction spans will be misplaced.
- Licenses for the prefilter. Intel Hyperscan stopped being open source after 5.4. Use Vectorscan (BSD-3); the PyPI 'hyperscan' package 0.9.1 (MIT) links Vectorscan statically by default. The 'regex' module 2026.9.29 is 'Apache-2.0 AND CNRI-Python', which is fine as a dependency.
- Excel: 15-significant-digit limit, missing from the recommendations. Numeric cells keep only 15 significant digits, so 16+ digit numbers (card numbers, long contract IDs) lose their last digits for good and then fail Luhn. A 15-digit NIR survives but displays as 1,23457E+14, and pandas or Markdown converters may render it as a float. Read raw values with openpyxl, not via pandas display.
- Excel dates: also handle the 1904 date system used by Mac workbooks and Excel's 1900 leap-year bug when turning serial numbers into dates.
- Excel: PII outside cell values, missing from the recommendations. Comments and threaded comments (with author names), headers and footers, sheet names, hidden sheets, rows and columns, defined names, data-validation lists, document properties (creator, lastModifiedBy), external links, embedded objects and VBA can all hold PII. So can pivot caches (pivotCacheRecords keep a full copy of the source data), chart caches and cached formula results (for example a concatenation of name cells keeps the old value until recalculated). Either sanitize these parts or strip them and warn.
- Excel libraries: openpyxl 3.1.5 (MIT) drops images and charts when it re-saves a workbook, and it keeps pivot tables but not their sanitized caches. For fidelity, editing the OOXML parts directly (sharedStrings, sheets) may be safer. python-calamine 0.9.0 (MIT) reads xls, xlsb and ods. pyxlsb 1.0.10 is LGPL-3+, so avoid it for .xlsb. Mention .xls, .xlsb, .ods and CSV, including the ';' separator and cp1252 encoding common in French exports.
- Legal framing is missing. Consistent column pseudonymization produces pseudonymised data (GDPR Art. 4(5)), which is still personal data for the controller. This is relevant to the EDPB Guidelines 01/2025 on pseudonymisation and to CJEU C-413/23 P EDPS v SRB (4 Sept 2025, recipient-relative view). French NIR use is also restricted (Loi Informatique et Libertés art. 30; décret n° 2019-341). These are from memory, not checked in this pass.
- Current versions found: python-stdnum 2.2 (still the latest), presidio-analyzer 2.2.364, Faker 40.43.0, schwifty 2026.10.0, phonenumbers 9.0.41, django-localflavor 5.1 (BSD-3-Clause). Faker fr_FR: confirmed that ssn() computes the NIR key with 2A/2B->19/18, that siren() and siret() compute Luhn, and that vat_id() keys are random. The RIB key in Faker was not checked.
- As oracles, stdnum's compact() strips only ' .' (NIR) or ' ' (NIF). Normalize NBSP and hyphens before comparing results.
- Limits of this check: the shared WebSearch budget was already exhausted, and the esante.gouv.fr pages and PDFs (RPPS/ADELI/FINESS guide, INS OID list) returned empty content to WebFetch. The RPPS Luhn rule, the ADELI end date and key, the NIA format and key, and FR EORI = FR+SIRET are still unverified against ANS and DGDDI primary sources.


