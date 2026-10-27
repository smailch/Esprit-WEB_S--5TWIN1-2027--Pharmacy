"""PrescriNLU-D — traducteur question française → SPARQL du module D (Prescription + Personne).

Chaîne 100 % locale et explicable (aucune API de LLM) :
  1. preprocessing      : normalisation (casse, accents, apostrophes, ponctuation) + spaCy (tokens, lemmes)
  2. lexicon            : dictionnaires métier générés depuis les libellés de l'ontologie (via SPARQL)
  3. entity_extractor   : spaCy PhraseMatcher + règles (identifiants, dates) + RapidFuzz (fautes de frappe)
  4. intent_classifier  : classifieur à règles pondérées sur lemmes et entités (indices affichés)
  5. sparql_generator   : gabarit SPARQL par intention, URI validées insérées via rdflib
  6. pipeline           : exécution RDFLib, réponse en français, explication pas à pas
"""
