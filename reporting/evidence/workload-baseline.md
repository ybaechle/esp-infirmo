# Charge et capacite initiales : preuve du cahier des charges

Audit du 15 septembre 2026. Source : [INFIRMO Cahier des Charges v4](../../docs/livrables/INFIRMO_Cahier_des_Charges_v4.pdf). Les pages ci-dessous sont les pages imprimees; ajouter 1 pour le numero de page du lecteur PDF.

**Le PDF contient bien les heures planifiees et les allocations individuelles.** Il ne contient pas de releve des heures effectivement consommees pendant le sprint ni d'ETC actualise. Les estimations de ses 83 tickets sont deja importees dans [effort.csv](../effort.csv).

## Budget par personne

Source : page 26, section 7.2; confirmation page 31, section 7.6. Conversion prescrite : **1 JH = 7 heures**. Les colonnes en heures sont calculees depuis les JH publies; elles ne mesurent pas le travail effectue.

| Personne | Travail productif (h) | Reunions (h, arrondi du PDF) | Budget initial (h) | Reserve avril (h) | Avec reserve (h) | Tickets importes, reunion incluse |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Tetiana Lombardi | 137.9 | 9.1 | 147 | 31.5 | 178.5 | 7 |
| Maxence Noizet | 137.9 | 9.1 | 147 | 31.5 | 178.5 | 9 |
| Yohan Baechlé | 137.9 | 9.1 | 147 | 31.5 | 178.5 | 10 |
| Lothaire Nobili  | 137.9 | 9.1 | 147 | 31.5 | 178.5 | 11 |
| Ziad Tiarimti | 137.9 | 9.1 | 147 | 31.5 | 178.5 | 12 |
| Pierre-Arthur Toutouom Yountebo | 137.9 | 9.1 | 147 | 31.5 | 178.5 | 15 |
| Lazaro Marrero Rousse | 137.9 | 9.1 | 147 | 31.5 | 178.5 | 19 |
| **Equipe** | **965.3** | **63.7** | **1029** | **220.5** | **1249.5** | **83** |

La reserve de 31.5 JH equipe est **en plus** des 147 JH initiaux; elle n'est pas une capacite deja consommee ni automatiquement disponible au sprint 1. Les sommes de `baseline_hours` ont ete verifiees : 147 h pour chacun des sept responsables, soit 1029 h au total.

**Precision d'arrondi :** le texte page 26 prevoit exactement 5 reunions de 1 h + 16 points de 15 min = 9 h par personne, soit 63 heures-personnes. Le tableau et les tickets MEET utilisent 1.3 JH, soit 9.1 h par personne. L'ecart de 0.1 h par personne vient de la conversion arrondie, pas d'un depassement mesure. Garder les 9.1 h comme baseline des tickets et comparer les durees reelles des rituels aux 9 h explicites; ne pas corriger silencieusement l'estimation historique.

## Origine des allocations

Pages 28-31, section 7.4 : chaque ticket a un responsable, une charge en JH, un milestone, une priorite et un WBS. Les totaux ci-dessus comprennent un ticket MEET par personne. PM-4 attribue deja **3 JH = 21 h** a Tetiana pour ScrumBan et le reporting. Cela permet d'utiliser le budget existant pour la consolidation, sans inventer un nouveau forfait.

Les tickets n'indiquent ni temps passe, ni pourcentage termine, ni reste a faire. Une estimation de ticket complet ne constitue pas une allocation du meme montant a cette seule demonstration.

## Capacite et dates des sprints

Le PDF page 44, section 11.1, mentionne des cycles de **5 JH par sprint**; [CONTRIBUTING.md](../../CONTRIBUTING.md) precise environ 5 JH de travail effectif par membre. Cela correspond a **environ 35 h par membre pour un cycle complet**, pas a un engagement confirme sur chaque plage calendaire.

Le PDF n'alloue pas de tickets ou d'heures par sprint numerote. Les dates suivantes proviennent de **CONTRIBUTING.md, section 4**, et non du PDF :

| Sprint | Dates publiees | Allocation horaire du sprint dans le PDF |
| --- | --- | --- |
| 1 | 11/09/2026 - 24/09/2026 | Non fournie |
| 2 | 25/09/2026 - 27/11/2026 | Non fournie |
| 3 | 30/11/2026 - 22/01/2027 | Non fournie |
| 4 | 29/01/2027 - 05/03/2027 | Non fournie |
| 5 | 12/03/2027 - 19/03/2027 | Non fournie |

Ne pas remplir automatiquement les cinq sprints avec 35 h par personne : cela ferait 175 h, au-dela des 147 h du budget initial. La repartition des jours disponibles et des tickets entre cycles doit etre confirmee en planification, en distinguant la reserve d'avril.

## Gouvernance et ecarts a rapprocher

- Page 34, section 9.2 : daily de 15 min; planning au debut du sprint, revue et retrospective en fin de sprint, chacun de 20 min. Il s'agit de la cadence prevue; aucune presence ou duree reelle n'est attestee.
- Page 35 : GitHub Projects est le suivi operationnel; les pages 45-46 demandent des tickets assignes, une revue de code et une validation en staging selon la DoD. Les tableaux du PDF ne remplacent pas leurs preuves d'execution.
- Page 43 : cible de couverture de 70% du coeur backend et pipeline de moins de 15 min. Ces seuils ne sont pas des mesures deja obtenues.
- **Ecart de calendrier source :** le PDF page 36 place M6 Securite/Deploy en avril 2027, alors que le README place M6 en mars et avril en reserve. La page 26 du PDF nomme deja avril comme reserve de finalisation. **Arbitrage du 17/09/2026 (Tetiana Lombardi) :** M6 est clos au plus tard le 31/03/2027; avril 2027 reste une reserve sans travail planifie, mais préparation à la soutenance. Le README et CONTRIBUTING font foi; le PDF source n'est pas reecrit retrospectivement (DL-014).

## Ce qui manque encore pour calculer la variance

La baseline est disponible. Il reste a recevoir, pour chaque tache active : les **heures reelles**, l'**ETC reestime**, et l'engagement de sprint valide. Le budget initial ne permet pas de deduire ces trois valeurs. Les comptes rendus de rituels, la validation par un pair et l'acceptation des echeances restent des observations humaines a recueillir.
