# Sécurité / Security

## Signaler une vulnérabilité / Reporting a vulnerability

**Français.** Ne signalez jamais une faille dans une issue publique, ni une donnée personnelle qui traverse
l'anonymisation sans être remplacée. Utilisez le signalement privé de GitHub :
[Report a vulnerability](https://github.com/FlowLineIntegration/GDPRGuardian/security/advisories/new), ou écrivez à
`contact@gardienrgpd.fr`. Décrivez le problème avec des données fictives uniquement, et indiquez l'impact estimé.
Nous accusons réception sous sept jours et publions un correctif avant toute divulgation.

**English.** Never report a vulnerability, or personal data passing through unmasked, in a public issue. Use GitHub
private reporting:
[Report a vulnerability](https://github.com/FlowLineIntegration/GDPRGuardian/security/advisories/new), or write to
`contact@gardienrgpd.fr`. Describe the problem with fictitious data only, and give the estimated impact. We
acknowledge within seven days and ship a fix before any disclosure.

## Périmètre / Scope

- Donnée personnelle qui traverse l'anonymisation sans être remplacée / personal data passing through unmasked.
- Toute voie permettant de retrouver une valeur d'origine à partir d'une balise / any way to recover an original
  value from a placeholder (le produit est conçu pour que ce soit impossible / the product is designed to make
  this impossible).
- Déni de service par fichier piégé (bombe ZIP, XML, PDF), contournement des limites du service public, fuite dans
  les journaux / denial of service via crafted files, bypass of the public service's limits, leaks into logs.

## Principes / Principles

- Aucune table de correspondance, clé éphémère par document, détruite après traitement / no mapping table, one
  ephemeral key per document, destroyed after processing.
- Aucun contenu dans les journaux ; traitement en mémoire uniquement / no content in logs; in-memory processing only.
- Analyse des fichiers dans un processus isolé avec limites de temps et de taille / files are parsed in an isolated
  process with time and size limits.
