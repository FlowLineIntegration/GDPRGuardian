# Contribuer / Contributing

1. Lire [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) : invariants (irréversibilité, aucun contenu dans les
   journaux, aucun LLM), contrats des détecteurs et des packs, conventions de code.
   Read the architecture document first: invariants, detector and pack contracts, coding conventions.
2. Identifiants en anglais ; commentaires courts et utiles, en français et en anglais.
   English identifiers; short, useful comments in French and English.
3. `uv sync --all-extras`, puis / then `uv run ruff check src tests` et / and `uv run pytest`.
4. Nouveau pays : un validateur par fichier (`src/gdprguardian/validators/<cc>.py`), un pack TOML
   (`src/gdprguardian/packs/data/<cc>.toml`), des tests avec des exemples officiels. Jamais de code copié
   depuis une bibliothèque sous LGPL ou GPL.
   New country: one validator module, one TOML pack, tests with official examples; never copy LGPL/GPL code.
5. Données de test : uniquement synthétiques. Jamais de vraies données personnelles dans le dépôt.
   Test data: synthetic only. Never real personal data in the repository.
