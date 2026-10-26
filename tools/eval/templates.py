# ruff: noqa: E501 - données de prose : un paragraphe = une ligne / prose data: one paragraph per line
"""Gabarits de documents français réalistes / realistic French document templates.

Syntaxe `str.format` : `{p1.full}` = mention annotée de la personne 1, `{c1.name}` = société,
`{d.amount}` = leurre (non personnel). Les civilités et accords (`{p1.civ}`, `{p1.e}`) sont du texte
simple, hors des zones (comme l'exige le contrat des détecteurs). Un gabarit peut être une fonction
`(rng) -> str` pour les tableaux à nombre de lignes variable.
`str.format` syntax: annotated person mentions, company fields, decoys; honorifics stay outside spans.
"""

from __future__ import annotations

from collections.abc import Callable
from random import Random

Template = str | Callable[[Random], str]

EMAIL: tuple[Template, ...] = (
    """De : {p1.full} <{p1.email}>
À : {p2.email}
Objet : Changement de coordonnées bancaires

Bonjour {p2.first},

Suite à mon changement de banque, pourriez-vous mettre à jour mes coordonnées pour le versement du salaire de {d.month} ?

Nouvel IBAN : {p1.iban}
Titulaire du compte : {p1.formal}

La prime exceptionnelle de {d.amount} prévue par l'accord du {d.date} peut être versée sur ce même compte.
Je reste joignable au {p1.phone}.

Merci d'avance et bonne journée,
{p1.full}
""",
    """Objet : Réclamation – commande {d.order}

Madame, Monsieur,

J'ai passé la commande {d.order} le {d.date} pour un montant de {d.amount}. Le paiement a été débité deux fois sur ma carte bancaire {p1.card}.
Merci de procéder au remboursement du doublon sur mon compte : {p1.iban}.

Mon numéro client : {p1.customer}.

Cordialement,
{p1.civ} {p1.formal}
{p1.address}
Tél. : {p1.phone}
""",
    """Subject: Onboarding – {p1.full}

Hi {p2.first},

Quick follow-up on the onboarding of {p1.full}, who joins the Lyon office on {d.date_iso}. {p1.his_cap} French social security number is {p1.nir} and {p1.his} bank details are IBAN {p1.iban}.
Please add {p1.email} to the payroll mailing list and call {p1.him} on {p1.phone} before Friday.

Thanks,
{p3.full}
""",
    """Objet : Re: Déménagement

Salut {p2.first} !

Ça y est, on a emménagé. Notre nouvelle adresse : {p1.address_inline}. Mon portable ne change pas ({p1.phone}), mais le fixe devient le {p1.landline}.
{p3.first} passe samedi vers {d.hour} si tu veux venir.

Bises,
{p1.first}
--
{p1.full} · {p1.email}
""",
)

MINUTES: tuple[Template, ...] = (
    """# Compte rendu – Comité de direction du {d.date}

**Présents :** {p1.full} (directeur général), {p2.full} (DRH), {p3.initial} (comptabilité), {p4.formal} (élu CSE)
**Excusé{p5.e} :** {p5.civ} {p5.last}

## 1. Recrutements
{p2.first} confirme l'embauche de {p6.full} ({p6.job}) à compter du {d.date}, pour une rémunération annuelle brute de {d.amount}. {p6.civ} {p6.last} sera joignable au {p6.phone} d'ici là.

## 2. Contentieux
Le litige opposant la société à {p7.civ_long} {p7.full} (RG n° {d.case}) est renvoyé au {d.date}. Conformément à l'article {d.article}, une médiation sera proposée ; {p1.first} se charge de recontacter {p7.civ} {p7.last}.

## 3. Budget
Le budget informatique est arrêté à {d.amount} ; la commande {d.order} (mise à jour {d.version}) est validée.

Prochaine réunion le {d.date}. Compte rendu rédigé par {p3.full} ({p3.email}).
""",
    """COMPTE RENDU DE L'ASSEMBLÉE GÉNÉRALE DU {d.date}

Ouverture de la séance à {d.hour} par {p1.civ_long} {p1.last_upper}, président{p1.e} de l'association.
Secrétaire de séance : {p2.full}.

Le rapport financier présenté par {p3.full} fait apparaître un excédent de {d.amount}. Les remboursements de frais aux bénévoles se feront désormais par virement (par exemple pour {p4.full}, IBAN {p4.iban}).

Questions diverses : {p5.full} ({p5.email}, {p5.phone}) propose d'organiser la fête annuelle le {d.date}. {p5.il_cap} rappelle que la salle doit être réservée avant le {d.date}.

La séance est levée à {d.hour}. Signé : {p1.full} et {p2.full}.
""",
)

HR_RECORD: tuple[Template, ...] = (
    """# Fiche individuelle – Dossier du personnel

| Rubrique | Information |
|---|---|
| Nom | {p1.last_upper} |
| Prénom | {p1.first} |
| Date de naissance | {p1.birth} |
| Lieu de naissance | {p1.birth_city} |
| N° de sécurité sociale | {p1.nir} |
| Adresse | {p1.address_inline} |
| Téléphone | {p1.phone} |
| E-mail personnel | {p1.email} |
| Matricule | {p1.staff_id} |
| Date d'entrée | {d.date_num} |
| Poste | {p1.job} |
| Salaire brut mensuel | {d.amount} |
| IBAN | {p1.iban} |
| Personne à prévenir | {p2.full} – {p2.phone} |
""",
    """AVENANT AU CONTRAT DE TRAVAIL

Entre la société {c1.name} {c1.form}, SIRET {c1.siret}, représentée par {p2.civ_long} {p2.full}, {p2.job},
et {p1.civ_long} {p1.formal}, {p1.ne} le {p1.birth_text} à {p1.birth_city}, demeurant {p1.address_inline}, numéro de sécurité sociale {p1.nir},

il est convenu ce qui suit.

Article 1 – À compter du {d.date}, la rémunération mensuelle brute de {p1.civ} {p1.last} est portée à {d.amount}.
Article 2 – Les autres clauses du contrat du {d.date}, conclu en application de l'article {d.article}, restent inchangées.

Fait à {d.city}, le {d.date}, en deux exemplaires.
{p2.full}                {p1.full}
""",
    """Note RH – Dossier d'embauche de {p1.full}

{p1.civ} {p1.last} ({p1.ne} le {p1.birth}, à {p1.birth_city}) rejoint l'équipe le {d.date_num}. Pièces reçues :
- passeport n° {p1.passport} ;
- carte nationale d'identité n° {p2.id_card} du conjoint, {p2.full} ;
- attestation de droits à l'assurance maladie (NIR {p1.nir}) ;
- RIB : {p1.rib}.

Date de naissance vérifiée : {p1.birth}, date d'entrée : {d.date_num}.
""",
)

CONTRACT: tuple[Template, ...] = (
    """CONTRAT DE LOCATION – LOCAL À USAGE D'HABITATION
(soumis à la loi n° {d.law})

ENTRE LES SOUSSIGNÉS :
{p1.civ_long} {p1.formal}, {p1.ne} le {p1.birth_text} à {p1.birth_city}, demeurant {p1.address_inline},
ci-après dénommé{p1.e} « le Bailleur »,

ET :
{p2.civ_long} {p2.formal}, {p2.ne} le {p2.birth_text} à {p2.birth_city}, titulaire de la carte nationale d'identité n° {p2.id_card}, joignable au {p2.phone},
ci-après dénommé{p2.e} « le Locataire ».

ARTICLE 1 – OBJET
Le Bailleur donne en location au Locataire le logement situé {p2.address_inline}.

ARTICLE 2 – LOYER
Le loyer mensuel est fixé à {d.amount}, charges comprises, payable le 5 de chaque mois par prélèvement sur le compte du Locataire (RIB {p2.rib}). Le dépôt de garantie s'élève à {d.amount}.

ARTICLE 3 – DURÉE
Le bail prend effet le {d.date} pour une durée de trois ans, conformément à l'article {d.article}.

Fait à {d.city}, le {d.date}.
Le Bailleur : {p1.full}                Le Locataire : {p2.full}
""",
    """CONTRAT DE PRESTATION DE SERVICES

Entre :
La société {c1.name} {c1.form}, au capital de {d.amount}, immatriculée au RCS sous le numéro {c1.siren}, représentée par {p2.civ_long} {p2.full} ({p2.job}), ci-après « le Client »,

Et :
{p1.civ_long} {p1.full}, entrepreneur individuel, SIRET {p1.siret}, domicilié{p1.e} {p1.address_inline}, ci-après « le Prestataire ».

Article 1 – Objet : le Prestataire réalise pour le Client la mission « {d.item} » (devis {d.order}).
Article 2 – Prix : {d.amount} HT par mois, payable à 30 jours par virement sur le compte {p1.iban}. TVA non applicable, article {d.vat_exempt}.
Article 3 – Données personnelles : chaque partie respecte l'article {d.article}.
Article 4 – Contact du Prestataire : {p1.email} – {p1.phone}.

Fait le {d.date}.
""",
    """CERTIFICAT DE CESSION D'UN VÉHICULE D'OCCASION

Vendeur : {p1.admin}, {p1.address_inline}
Acheteur : {p2.admin}, {p2.ne} le {p2.birth}, {p2.address_inline}

Véhicule immatriculé {p1.plate} (ancienne immatriculation {p1.plate_old}), première mise en circulation le {d.date_num}, kilométrage : {d.km} km.
Prix de vente : {d.amount}, réglé par virement.

Fait à {d.city}, le {d.date}, à {d.hour}.
Signatures : {p1.full} / {p2.full}
""",
)

INVOICE: tuple[Template, ...] = (
    """FACTURE N° {d.invoice}
Date d'émission : {d.date_num} – Échéance : {d.date_num}

{p1.full} – Entrepreneur individuel (EI)
{p1.address}
SIRET : {p1.siret}
N° TVA intracommunautaire : {p1.vat}
{p1.phone} – {p1.email}

Facturé à :
{c1.name} {c1.form}
SIRET : {c1.siret}
À l'attention de {p2.civ} {p2.full}

| Désignation | Référence | Qté | PU HT | Total HT |
|---|---|---|---|---|
| {d.item} | {d.ref} | 2 | {d.amount} | {d.amount} |
| {d.item} | {d.ref} | 1 | {d.amount} | {d.amount} |

Total TTC : {d.amount}
Règlement par virement – IBAN : {p1.iban} – BIC : {d.bic}
En cas de retard, pénalités prévues à l'article {d.article}. Commande client : {d.order}.
""",
    """{c1.name} {c1.form} – SIREN {c1.siren} – TVA {c1.vat}

FACTURE {d.invoice} du {d.date}

Client : {p1.civ} {p1.formal}
{p1.address}
Réf. client : {p1.customer}

| Article | Code EAN | Montant TTC |
|---|---|---|
| {d.item} | {d.ean} | {d.amount} |
| Frais de livraison | – | {d.amount} |

Payé par carte bancaire le {d.date}. Suivi du colis : {d.tracking}.
Service clients : {p2.full}, {p2.email}.
""",
    """Facture d'électricité – {d.month} {d.year}

Titulaire du contrat : {p1.admin}
Adresse de consommation : {p1.address_inline}
N° de PDL : {p1.pdl}
Référence client : {p1.customer}

Consommation de la période : {d.kwh} kWh
Montant TTC : {d.amount}, prélevé le {d.date} sur le compte {p1.iban}.
Fournisseur : {c1.name} {c1.form}, SIRET {c1.siret}.
""",
)

TICKET: tuple[Template, ...] = (
    """Ticket #{d.ticket} – Priorité : haute – Ouvert le {d.date_num}
Client : {p1.full} (n° client : {p1.customer})
Canal : e-mail ({p1.email})

Message du client :
Bonjour, depuis la mise à jour {d.version} je ne peux plus me connecter à mon espace. Mon adresse IP est {p1.ip}, au cas où elle serait bloquée. Vous pouvez me rappeler au {p1.phone} après {d.hour}.

Réponse de {p2.first} (support niveau 2) :
Bonjour {p1.civ} {p1.last}, votre IP figurait bien sur liste noire après plusieurs échecs de connexion ; elle est débloquée. Merci de vérifier que l'adresse {p1.email} est bien celle de votre compte.

Statut : résolu.
""",
    """[Support] Ticket {d.ticket} – Livraison non reçue

{p1.first} {p1.last_upper} a écrit :
> Commande {d.order}, colis {d.tracking}, toujours pas livré à l'adresse {p1.address_inline}. J'ai payé avec ma carte {p1.card}. Je suis joignable au {p1.phone}.

Réponse de {p2.full} :
Le transporteur indique une livraison le {d.date}. Nous ouvrons une enquête et vous remboursons {d.amount} sur votre moyen de paiement d'origine.
""",
    """Ticket {d.ticket} – Account locked

From: {p1.email}
Customer: {p1.full}, {p1.address_inline}

Hello, I can't access my account since version {d.version}. My phone number is {p1.phone} and my IBAN for the refund is {p1.iban}. Thanks!

Agent note: identity checked against passport {p1.passport} (French passport).
""",
)

MEDICAL: tuple[Template, ...] = (
    """Service de cardiologie – Consultation du {d.date}
Dr {p1.full}
RPPS : {p1.rpps}

{d.city}, le {d.date}

Cher confrère,

Je vous adresse {p2.civ_long} {p2.full}, {p2.ne} le {p2.birth} (N° IPP : {p2.ipp}), domicilié{p2.e} {p2.address_inline}, que j'ai vu{p2.e} ce jour pour {d.symptom}.
L'examen clinique est rassurant ; l'ECG montre un rythme sinusal régulier. Je propose une échographie cardiaque et un Holter.

Numéro de sécurité sociale : {p2.nir}. Prise en charge à 100 % (ALD).
{p2.il_cap} est joignable au {p2.phone}. Établissement : FINESS {d.finess}.

Bien confraternellement,
Dr {p1.last}
""",
    """ORDONNANCE

Dr {p1.formal} – Médecin généraliste
{p1.address}
N° RPPS {p1.rpps} – Tél. cabinet {p1.landline}

Le {d.date}

{p2.civ} {p2.full}, {d.age} ans
Né{p2.e} le {p2.birth}
N° d'immatriculation : {p2.nir13}

1. Bisoprolol 2,5 mg : 1 comprimé le matin pendant 3 mois.
2. Atorvastatine 20 mg : 1 comprimé le soir.

Renouvelable 2 fois.
""",
)


def _staff_export(rng: Random) -> str:
    rows = rng.randint(3, 7)
    lines = ["# Export RH – effectifs au {d.date_num}", "",
             "| Matricule | Nom | Prénom | Date de naissance | N° SS | Téléphone | E-mail |",
             "|---|---|---|---|---|---|---|"]
    lines += [f"| {{p{i}.staff_id}} | {{p{i}.last_upper}} | {{p{i}.first}} | {{p{i}.birth}} | {{p{i}.nir}} "
              f"| {{p{i}.phone}} | {{p{i}.email}} |" for i in range(1, rows + 1)]
    lines += ["", f"Total : {rows} salariés. Masse salariale mensuelle : {{d.amount}}."]
    return "\n".join(lines) + "\n"


def _attendance(rng: Random) -> str:
    rows = rng.randint(3, 8)
    lines = ["## Liste d'émargement – formation « {d.item} » du {d.date}", "",
             "| Participant | Société | E-mail | Téléphone | Signature |", "|---|---|---|---|---|"]
    lines += [f"| {{p{i}.full}} | {{c{i}.name}} | {{p{i}.email}} | {{p{i}.phone}} | signé |"
              for i in range(1, rows + 1)]
    return "\n".join(lines) + "\n"


def _customers(rng: Random) -> str:
    rows = rng.randint(3, 6)
    lines = ["### Clients en retard de paiement au {d.date}", "",
             "| Client | Ville | Téléphone | IBAN | Solde dû |", "|---|---|---|---|---|"]
    lines += [f"| {{p{i}.admin}} | {{p{i}.home_city}} | {{p{i}.phone}} | {{p{i}.iban}} | {{d.amount}} |"
              for i in range(1, rows + 1)]
    lines += ["", "Relance automatique prévue sous huit jours."]
    return "\n".join(lines) + "\n"


TABLE: tuple[Template, ...] = (_staff_export, _attendance, _customers)

LETTER: tuple[Template, ...] = (
    """Caisse d'allocations familiales
{d.city}, le {d.date}

{p1.civ_long} {p1.formal}
{p1.address}

N° allocataire : {p1.caf}
Objet : révision de vos droits

{p1.civ_long},

Suite à votre déclaration trimestrielle, le montant de votre aide personnalisée au logement est fixé à {d.amount} par mois à compter du {d.date}. Il sera versé sur votre compte {p1.iban}.
Pour toute démarche, munissez-vous de votre numéro allocataire et de votre numéro de sécurité sociale ({p1.nir}).
""",
    """France Travail – Agence de {d.city}

{p1.civ_long} {p1.full}
Identifiant France Travail : {p1.france_travail}

Objet : convocation à un entretien

{p1.civ_long},

Vous êtes convoqué{p1.e} le {d.date} à {d.hour} pour un entretien avec votre conseiller, {p2.full}. Merci de vous munir d'une pièce d'identité et de votre CV. En cas d'empêchement, contactez {p2.first} au {p2.landline} ou à {p2.email}.
""",
    """DIRECTION GÉNÉRALE DES FINANCES PUBLIQUES
Avis d'imposition {d.year} – revenus de l'année précédente

Déclarant 1 : {p1.admin} – numéro fiscal {p1.spi}
Déclarant 2 : {p2.admin} – numéro fiscal {p2.spi}
Adresse : {p1.address_inline}

Revenu fiscal de référence : {d.amount}
Montant de l'impôt : {d.amount}, prélevé sur le compte {p1.iban}.
""",
    """AVIS DE CONTRAVENTION
Infraction constatée le {d.date} à {d.hour} : excès de vitesse inférieur à 20 km/h.

Véhicule : immatriculation {p1.plate}
Titulaire du certificat d'immatriculation : {p1.admin}
Adresse : {p1.address_inline}

Montant de l'amende forfaitaire : {d.amount}, payable jusqu'au {d.date} (article {d.road_article}).
""",
    """RELEVÉ D'IDENTITÉ BANCAIRE

Titulaire : {p1.admin}
{p1.address}

{p1.rib_split}

IBAN : {p1.iban}
BIC : {d.bic}
Domiciliation : agence de {d.city}
""",
    """URSSAF – Déclaration de chiffre d'affaires

{p1.civ_long} {p1.full}
Micro-entrepreneur – SIREN {p1.siren}
{p1.address}

Période déclarée : {d.month} {d.year}
Chiffre d'affaires déclaré : {d.amount}
Cotisations sociales dues : {d.amount}, prélevées le {d.date} sur le compte {p1.iban}.
""",
    """La Poste – Service clients courrier
SIRET {d.laposte_siret}

{p1.civ_long} {p1.full}
{p1.address}

Objet : votre réclamation du {d.date} (lettre recommandée {d.tracking})

{p1.civ_long},

Nous avons bien reçu votre réclamation. Une indemnisation de {d.amount} vous sera versée par virement sur le compte {p1.iban} sous quinze jours.
""",
)

TEMPLATES: dict[str, tuple[Template, ...]] = {
    "email": EMAIL,
    "minutes": MINUTES,
    "hr_record": HR_RECORD,
    "contract": CONTRACT,
    "invoice": INVOICE,
    "ticket": TICKET,
    "medical": MEDICAL,
    "table": TABLE,
    "letter": LETTER,
}
KINDS: tuple[str, ...] = tuple(TEMPLATES)
# Gabarits rédigés en anglais (identifiants français) / templates written in English (French identifiers).
ENGLISH_TEMPLATES: frozenset[tuple[str, int]] = frozenset({("email", 2), ("ticket", 2)})
