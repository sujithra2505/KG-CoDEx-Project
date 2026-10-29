# Phase 5: rule-based predictions (round 1)

Predicted triples are **hypotheses**, not facts. They come from statistical rule patterns in
the training graph and were **not** checked against validation or test data (that is Phase 6).

- Training graph: `outputs/phase2/training_graph.graphml` (185,584 edges)
- Rules: `outputs/phase4/phase5_candidate_rules_proposed.json` (160 frozen rules, SHA-256 `3723c68a6237…`)
- Rounds: 1; cap: 100 per relation
- Ranking score: `max_wilson_lower` = highest Wilson lower bound among the supporting rules
- Tie-break: max_pca_confidence desc, supporting_rules desc, subject ID number asc, object ID number asc

## Counts

- Candidate records (rule × pair): 212,342
- Body pairs skipped because the head triple is already in training: 65,813
- Duplicate records merged (same triple from several rules): 27,855
- Unique candidate triples: 184,487
- Retained after the per-relation cap: **3,239** (1,396 supported by more than one rule)
- Score tiers: 0.4–0.7: 1,036, < 0.4: 1,425, ≥ 0.7: 778

## Per relation

| Relation | Candidates | Retained | Top score | Lowest retained score |
|---|---:|---:|---:|---:|
| country (P17) | 4,733 | 100 | 0.759 | 0.447 |
| place of birth (P19) | 17,579 | 100 | 0.663 | 0.663 |
| place of death (P20) | 19,928 | 100 | 0.259 | 0.259 |
| spouse (P26) | 496 | 100 | 0.918 | 0.918 |
| country of citizenship (P27) | 32,283 | 100 | 0.810 | 0.810 |
| continent (P30) | 126 | 100 | 0.674 | 0.530 |
| official language (P37) | 3,488 | 100 | 0.507 | 0.473 |
| child (P40) | 39 | 39 | 0.891 | 0.663 |
| educated at (P69) | 3,540 | 100 | 0.226 | 0.226 |
| field of work (P101) | 974 | 100 | 0.230 | 0.230 |
| member of political party (P102) | 272 | 100 | 0.668 | 0.541 |
| occupation (P106) | 14,439 | 100 | 0.374 | 0.374 |
| employer (P108) | 8,011 | 100 | 0.228 | 0.228 |
| place of burial (P119) | 123 | 100 | 0.478 | 0.377 |
| located in the administrative terroritorial entity (P131) | 3,576 | 100 | 0.655 | 0.655 |
| movement (P135) | 460 | 100 | 0.259 | 0.259 |
| genre (P136) | 4,442 | 100 | 0.188 | 0.188 |
| religion (P140) | 2,005 | 100 | 0.386 | 0.386 |
| headquarters location (P159) | 160 | 100 | 0.627 | 0.627 |
| cast member (P161) | 379 | 100 | 0.360 | 0.360 |
| ethnic group (P172) | 15,063 | 100 | 0.753 | 0.366 |
| record label (P264) | 145 | 100 | 0.309 | 0.309 |
| part of (P361) | 895 | 100 | 0.186 | 0.186 |
| unmarried partner (P451) | 908 | 100 | 0.807 | 0.240 |
| member of (P463) | 9,673 | 100 | 0.300 | 0.300 |
| country of origin (P495) | 2,968 | 100 | 0.718 | 0.718 |
| cause of death (P509) | 246 | 100 | 0.514 | 0.514 |
| diplomatic relation (P530) | 3,938 | 100 | 0.770 | 0.770 |
| residence (P551) | 20,713 | 100 | 0.411 | 0.411 |
| narrative location (P840) | 633 | 100 | 0.096 | 0.096 |
| instrument (P1303) | 791 | 100 | 0.417 | 0.417 |
| languages spoken, written, or signed (P1412) | 11,336 | 100 | 0.783 | 0.783 |
| sibling (P3373) | 125 | 100 | 0.957 | 0.807 |

## Top 3 predictions per relation

**country (P17)**
- #1 New York (Q1384) → United States of America (Q30) — score 0.759; 8 rule(s); best `P740(y,x) & P495(y,z) => P17(x,z)`; evidence: Q162586 P740 Q1384; Q162586 P495 Q30
- #2 London (Q84) → United States of America (Q30) — score 0.759; 7 rule(s); best `P740(y,x) & P495(y,z) => P17(x,z)`; evidence: Q201607 P740 Q84; Q201607 P495 Q30
- #3 Dublin (Q1761) → Ireland (Q27) — score 0.759; 6 rule(s); best `P740(y,x) & P495(y,z) => P17(x,z)`; evidence: Q202314 P740 Q1761; Q202314 P495 Q27

**place of birth (P19)**
- #1 Wilhelm von Humboldt (Q77888) → Berlin (Q64) — score 0.663; 4 rule(s); best `P3373(x,y) & P19(y,z) => P19(x,z)`; evidence: Q77888 P3373 Q6694; Q6694 P19 Q64
- #2 Jürgen Kuczynski (Q88427) → Berlin (Q64) — score 0.663; 4 rule(s); best `P3373(x,y) & P19(y,z) => P19(x,z)`; evidence: Q88427 P3373 Q75151; Q75151 P19 Q64
- #3 Nelson Rockefeller (Q11237) → New York City (Q60) — score 0.663; 3 rule(s); best `P3373(x,y) & P19(y,z) => P19(x,z)`; evidence: Q11237 P3373 Q11239; Q11239 P19 Q60

**place of death (P20)**
- #1 Borys Paton (Q2704774) → Kiev (Q1899) — score 0.259; 5 rule(s); best `P551(x,z) => P20(x,z)`; evidence: Q2704774 P551 Q1899
- #2 Eric Schmidt (Q92747) → Washington, D.C. (Q61) — score 0.259; 4 rule(s); best `P551(x,z) => P20(x,z)`; evidence: Q92747 P551 Q61
- #3 Fernando del Paso Morante (Q557774) → Mexico City (Q1489) — score 0.259; 4 rule(s); best `P551(x,z) => P20(x,z)`; evidence: Q557774 P551 Q1489

**spouse (P26)**
- #1 Jada Pinkett Smith (Q228787) → Will Smith (Q40096) — score 0.918; 3 rule(s); best `P26(z,x) => P26(x,z)`; evidence: Q40096 P26 Q228787
- #2 Roberto Rossellini (Q53003) → Ingrid Bergman (Q43247) — score 0.918; 2 rule(s); best `P26(z,x) => P26(x,z)`; evidence: Q43247 P26 Q53003
- #3 Michael Verhoeven (Q67641) → Senta Berger (Q62310) — score 0.918; 2 rule(s); best `P26(z,x) => P26(x,z)`; evidence: Q62310 P26 Q67641

**country of citizenship (P27)**
- #1 Jennifer Grey (Q232927) → United States of America (Q30) — score 0.810; 6 rule(s); best `P69(x,y) & P17(y,z) => P27(x,z)`; evidence: Q232927 P69 Q993267; Q993267 P17 Q30
- #2 Gustav Mahler (Q7304) → Austria (Q40) — score 0.810; 5 rule(s); best `P69(x,y) & P17(y,z) => P27(x,z)`; evidence: Q7304 P69 Q686522; Q686522 P17 Q40
- #3 Ernst Fuchs (Q112856) → Austria (Q40) — score 0.810; 5 rule(s); best `P69(x,y) & P17(y,z) => P27(x,z)`; evidence: Q112856 P69 Q414219; Q414219 P17 Q40

**continent (P30)**
- #1 Russia (Q159) → Europe (Q46) — score 0.674; 2 rule(s); best `P131(y,x) & P30(y,z) => P30(x,z)`; evidence: Q656 P131 Q159; Q656 P30 Q46
- #2 Soviet Union (Q15180) → Eurasia (Q5401) — score 0.674; 2 rule(s); best `P131(y,x) & P30(y,z) => P30(x,z)`; evidence: Q2184 P131 Q15180; Q2184 P30 Q5401
- #3 Russian Empire (Q34266) → Europe (Q46) — score 0.674; 2 rule(s); best `P131(y,x) & P30(y,z) => P30(x,z)`; evidence: Q656 P131 Q34266; Q656 P30 Q46

**official language (P37)**
- #1 Switzerland (Q39) → French (Q150) — score 0.507; 3 rule(s); best `P17(y,x) & P37(y,z) => P37(x,z)`; evidence: Q807 P17 Q39; Q807 P37 Q150
- #2 France (Q142) → Italian (Q652) — score 0.507; 3 rule(s); best `P17(y,x) & P37(y,z) => P37(x,z)`; evidence: Q1449 P17 Q142; Q1449 P37 Q652
- #3 Ukraine (Q212) → Russian (Q7737) — score 0.507; 3 rule(s); best `P17(y,x) & P37(y,z) => P37(x,z)`; evidence: Q7525 P17 Q212; Q7525 P37 Q7737

**child (P40)**
- #1 Thomas Mann (Q37030) → Klaus Mann (Q77087) — score 0.891; 3 rule(s); best `P40(x,y) & P3373(z,y) => P40(x,z)`; evidence: Q37030 P40 Q61597; Q77087 P3373 Q61597
- #2 Yoko Ono (Q117012) → Julian Lennon (Q357974) — score 0.891; 3 rule(s); best `P40(x,y) & P3373(z,y) => P40(x,z)`; evidence: Q117012 P40 Q311238; Q357974 P3373 Q311238
- #3 Connie Stevens (Q262507) → Carrie Fisher (Q108941) — score 0.891; 3 rule(s); best `P40(x,y) & P3373(z,y) => P40(x,z)`; evidence: Q262507 P40 Q254789; Q108941 P3373 Q254789

**educated at (P69)**
- #1 Douglas Adams (Q42) → British Broadcasting Corporation (Q9531) — score 0.226; 1 rule(s); best `P108(x,z) => P69(x,z)`; evidence: Q42 P108 Q9531
- #2 Barack Obama (Q76) → University of Chicago (Q131252) — score 0.226; 1 rule(s); best `P108(x,z) => P69(x,z)`; evidence: Q76 P108 Q131252
- #3 Tim Berners-Lee (Q80) → Massachusetts Institute of Technology (Q49108) — score 0.226; 1 rule(s); best `P108(x,z) => P69(x,z)`; evidence: Q80 P108 Q49108

**field of work (P101)**
- #1 Arthur Rimbaud (Q493) → poetry (Q482) — score 0.230; 2 rule(s); best `P737(y,x) & P101(y,z) => P101(x,z)`; evidence: Q120381 P737 Q493; Q120381 P101 Q482
- #2 Albert Einstein (Q937) → metaphysics (Q35277) — score 0.230; 2 rule(s); best `P737(y,x) & P101(y,z) => P101(x,z)`; evidence: Q42156 P737 Q937; Q42156 P101 Q35277
- #3 Fyodor Dostoyevsky (Q991) → philosophy (Q5891) — score 0.230; 2 rule(s); best `P737(y,x) & P101(y,z) => P101(x,z)`; evidence: Q27645 P737 Q991; Q27645 P101 Q5891

**member of political party (P102)**
- #1 Barbara Pierce Bush (Q153730) → Republican Party (Q29468) — score 0.668; 3 rule(s); best `P3373(y,x) & P102(y,z) => P102(x,z)`; evidence: Q153481 P3373 Q153730; Q153481 P102 Q29468
- #2 Kelly Curtis (Q273574) → Democratic Party (Q29552) — score 0.668; 3 rule(s); best `P3373(y,x) & P102(y,z) => P102(x,z)`; evidence: Q106997 P3373 Q273574; Q106997 P102 Q29552
- #3 Rory Kennedy (Q273833) → Democratic Party (Q29552) — score 0.668; 3 rule(s); best `P3373(y,x) & P102(y,z) => P102(x,z)`; evidence: Q1386420 P3373 Q273833; Q1386420 P102 Q29552

**occupation (P106)**
- #1 Michael Jackson (Q2831) → singer (Q177220) — score 0.374; 6 rule(s); best `P3373(y,x) & P106(y,z) => P106(x,z)`; evidence: Q131324 P3373 Q2831; Q131324 P106 Q177220
- #2 Michael Jackson (Q2831) → television actor (Q10798782) — score 0.374; 6 rule(s); best `P3373(y,x) & P106(y,z) => P106(x,z)`; evidence: Q131324 P3373 Q2831; Q131324 P106 Q10798782
- #3 Michael Jackson (Q2831) → songwriter (Q753110) — score 0.374; 5 rule(s); best `P3373(y,x) & P106(y,z) => P106(x,z)`; evidence: Q234388 P3373 Q2831; Q234388 P106 Q753110

**employer (P108)**
- #1 Douglas Adams (Q42) → St John's College (Q691283) — score 0.228; 1 rule(s); best `P69(x,z) => P108(x,z)`; evidence: Q42 P69 Q691283
- #2 Barack Obama (Q76) → Columbia University (Q49088) — score 0.228; 1 rule(s); best `P69(x,z) => P108(x,z)`; evidence: Q76 P69 Q49088
- #3 Barack Obama (Q76) → Harvard Law School (Q49122) — score 0.228; 1 rule(s); best `P69(x,z) => P108(x,z)`; evidence: Q76 P69 Q49122

**place of burial (P119)**
- #1 Soong Ching-ling (Q17132) → Ferncliff Cemetery (Q1771319) — score 0.478; 1 rule(s); best `P3373(x,y) & P119(y,z) => P119(x,z)`; evidence: Q17132 P3373 Q17135; Q17135 P119 Q1771319
- #2 Sándor Márai (Q36951) → Farkasréti Cemetery (Q996499) — score 0.478; 1 rule(s); best `P3373(x,y) & P119(y,z) => P119(x,z)`; evidence: Q36951 P3373 Q386394; Q386394 P119 Q996499
- #3 Thomas Mann (Q37030) → Dorotheenstadt cemetery (Q564922) — score 0.478; 1 rule(s); best `P3373(x,y) & P119(y,z) => P119(x,z)`; evidence: Q37030 P3373 Q76480; Q76480 P119 Q564922

**located in the administrative terroritorial entity (P131)**
- #1 Atlantic Records (Q202440) → United States of America (Q30) — score 0.655; 2 rule(s); best `P159(x,z) => P131(x,z)`; evidence: Q202440 P159 Q30
- #2 Parlophone (Q208909) → Germany (Q183) — score 0.655; 2 rule(s); best `P159(x,z) => P131(x,z)`; evidence: Q208909 P159 Q183
- #3 EMI Records (Q3629023) → United Kingdom (Q145) — score 0.655; 2 rule(s); best `P159(x,z) => P131(x,z)`; evidence: Q3629023 P159 Q145

**movement (P135)**
- #1 Émile Zola (Q504) → literary realism (Q667661) — score 0.259; 2 rule(s); best `P737(y,x) & P135(y,z) => P135(x,z)`; evidence: Q5685 P737 Q504; Q5685 P135 Q667661
- #2 Karl Marx (Q9061) → atheism (Q7066) — score 0.259; 2 rule(s); best `P737(y,x) & P135(y,z) => P135(x,z)`; evidence: Q27645 P737 Q9061; Q27645 P135 Q7066
- #3 Guy de Maupassant (Q9327) → literary realism (Q667661) — score 0.259; 2 rule(s); best `P737(y,x) & P135(y,z) => P135(x,z)`; evidence: Q230476 P737 Q9327; Q230476 P135 Q667661

**genre (P136)**
- #1 Elvis Presley (Q303) → hip hop music (Q11401) — score 0.188; 2 rule(s); best `P737(y,x) & P136(y,z) => P136(x,z)`; evidence: Q4235 P737 Q303; Q4235 P136 Q11401
- #2 Elvis Presley (Q303) → pop music (Q37073) — score 0.188; 2 rule(s); best `P737(y,x) & P136(y,z) => P136(x,z)`; evidence: Q4235 P737 Q303; Q4235 P136 Q37073
- #3 Elvis Presley (Q303) → country music (Q83440) — score 0.188; 2 rule(s); best `P737(y,x) & P136(y,z) => P136(x,z)`; evidence: Q4235 P737 Q303; Q4235 P136 Q83440

**religion (P140)**
- #1 Wernher von Braun (Q57384) → Lutheranism (Q75809) — score 0.386; 2 rule(s); best `P3373(y,x) & P140(y,z) => P140(x,z)`; evidence: Q85426 P3373 Q57384; Q85426 P140 Q75809
- #2 Klaus Mann (Q77087) → Lutheranism (Q75809) — score 0.386; 2 rule(s); best `P3373(y,x) & P140(y,z) => P140(x,z)`; evidence: Q77109 P3373 Q77087; Q77109 P140 Q75809
- #3 Napoleon (Q517) → Catholic Church (Q9592) — score 0.386; 1 rule(s); best `P3373(y,x) & P140(y,z) => P140(x,z)`; evidence: Q151087 P3373 Q517; Q151087 P140 Q9592

**headquarters location (P159)**
- #1 England (Q21) → United Kingdom (Q145) — score 0.627; 1 rule(s); best `P131(x,z) => P159(x,z)`; evidence: Q21 P131 Q145
- #2 England (Q21) → United Kingdom of Great Britain and Ireland (Q174193) — score 0.627; 1 rule(s); best `P131(x,z) => P159(x,z)`; evidence: Q21 P131 Q174193
- #3 Scotland (Q22) → United Kingdom of Great Britain and Ireland (Q174193) — score 0.627; 1 rule(s); best `P131(x,z) => P159(x,z)`; evidence: Q22 P131 Q174193

**cast member (P161)**
- #1 The Manchurian Candidate (Q3589) → Jonathan Demme (Q48987) — score 0.360; 1 rule(s); best `P57(x,z) => P161(x,z)`; evidence: Q3589 P57 Q48987
- #2 Cleopatra (Q4430) → Joseph L. Mankiewicz (Q51583) — score 0.360; 1 rule(s); best `P57(x,z) => P161(x,z)`; evidence: Q4430 P57 Q51583
- #3 Cleopatra (Q4430) → Darryl F. Zanuck (Q364342) — score 0.360; 1 rule(s); best `P57(x,z) => P161(x,z)`; evidence: Q4430 P57 Q364342

**ethnic group (P172)**
- #1 Robert Siodmak (Q51498) → Germans (Q42884) — score 0.753; 2 rule(s); best `P3373(x,y) & P172(y,z) => P172(x,z)`; evidence: Q51498 P3373 Q77489; Q77489 P172 Q42884
- #2 Monika Mann (Q71407) → Germans (Q42884) — score 0.753; 2 rule(s); best `P3373(x,y) & P172(y,z) => P172(x,z)`; evidence: Q71407 P3373 Q214191; Q214191 P172 Q42884
- #3 Elisabeth Mann Borgese (Q71819) → Germans (Q42884) — score 0.753; 2 rule(s); best `P3373(x,y) & P172(y,z) => P172(x,z)`; evidence: Q71819 P3373 Q214191; Q214191 P172 Q42884

**record label (P264)**
- #1 Bob Dylan (Q392) → Warner Bros. (Q126399) — score 0.309; 1 rule(s); best `P463(x,y) & P264(y,z) => P264(x,z)`; evidence: Q392 P463 Q332399; Q332399 P264 Q126399
- #2 Bob Dylan (Q392) → Warner Bros. Records (Q843402) — score 0.309; 1 rule(s); best `P463(x,y) & P264(y,z) => P264(x,z)`; evidence: Q392 P463 Q332399; Q332399 P264 Q843402
- #3 Tupac Shakur (Q6107) → Warner Bros. Records (Q843402) — score 0.309; 1 rule(s); best `P463(x,y) & P264(y,z) => P264(x,z)`; evidence: Q6107 P463 Q605778; Q605778 P264 Q843402

**part of (P361)**
- #1 Canada (Q16) → South America (Q18) — score 0.186; 1 rule(s); best `P530(y,x) & P361(y,z) => P361(x,z)`; evidence: Q155 P530 Q16; Q155 P361 Q18
- #2 Canada (Q16) → Europe (Q46) — score 0.186; 1 rule(s); best `P530(y,x) & P361(y,z) => P361(x,z)`; evidence: Q20 P530 Q16; Q20 P361 Q46
- #3 Canada (Q16) → European Union (Q458) — score 0.186; 1 rule(s); best `P530(y,x) & P361(y,z) => P361(x,z)`; evidence: Q145 P530 Q16; Q145 P361 Q458

**unmarried partner (P451)**
- #1 Paul Simon (Q4028) → Carrie Fisher (Q108941) — score 0.807; 3 rule(s); best `P451(z,x) => P451(x,z)`; evidence: Q108941 P451 Q4028
- #2 Brad Pitt (Q35332) → Jennifer Aniston (Q32522) — score 0.807; 3 rule(s); best `P451(z,x) => P451(x,z)`; evidence: Q32522 P451 Q35332
- #3 Jeff Goldblum (Q106706) → Laura Dern (Q220901) — score 0.807; 3 rule(s); best `P451(z,x) => P451(x,z)`; evidence: Q220901 P451 Q106706

**member of (P463)**
- #1 Africa (Q15) → United Nations (Q1065) — score 0.300; 1 rule(s); best `P530(y,x) & P463(y,z) => P463(x,z)`; evidence: Q148 P530 Q15; Q148 P463 Q1065
- #2 Africa (Q15) → UNESCO (Q7809) — score 0.300; 1 rule(s); best `P530(y,x) & P463(y,z) => P463(x,z)`; evidence: Q148 P530 Q15; Q148 P463 Q7809
- #3 Africa (Q15) → World Trade Organization (Q7825) — score 0.300; 1 rule(s); best `P530(y,x) & P463(y,z) => P463(x,z)`; evidence: Q148 P530 Q15; Q148 P463 Q7825

**country of origin (P495)**
- #1 More Than a Miracle (Q31786) → Italy (Q38) — score 0.718; 3 rule(s); best `P57(x,y) & P27(y,z) => P495(x,z)`; evidence: Q31786 P57 Q53050; Q53050 P27 Q38
- #2 The Proposal (Q108586) → United States of America (Q30) — score 0.718; 3 rule(s); best `P57(x,y) & P27(y,z) => P495(x,z)`; evidence: Q108586 P57 Q242557; Q242557 P27 Q30
- #3 Vanilla Sky (Q110278) → United States of America (Q30) — score 0.718; 3 rule(s); best `P57(x,y) & P27(y,z) => P495(x,z)`; evidence: Q110278 P57 Q318287; Q318287 P27 Q30

**cause of death (P509)**
- #1 Galileo Galilei (Q307) → blindness (Q10874) — score 0.514; 1 rule(s); best `P1050(x,z) => P509(x,z)`; evidence: Q307 P1050 Q10874
- #2 Stendhal (Q502) → syphilis (Q41083) — score 0.514; 1 rule(s); best `P1050(x,z) => P509(x,z)`; evidence: Q502 P1050 Q41083
- #3 Napoleon (Q517) → epilepsy (Q41571) — score 0.514; 1 rule(s); best `P1050(x,z) => P509(x,z)`; evidence: Q517 P1050 Q41571

**diplomatic relation (P530)**
- #1 Canada (Q16) → France (Q142) — score 0.770; 3 rule(s); best `P530(z,x) => P530(x,z)`; evidence: Q142 P530 Q16
- #2 United States of America (Q30) → Netherlands (Q55) — score 0.770; 3 rule(s); best `P530(z,x) => P530(x,z)`; evidence: Q55 P530 Q30
- #3 United States of America (Q30) → Czech Republic (Q213) — score 0.770; 3 rule(s); best `P530(z,x) => P530(x,z)`; evidence: Q213 P530 Q30

**residence (P551)**
- #1 Frederick William III of Prussia (Q37134) → Berlin (Q64) — score 0.411; 3 rule(s); best `P20(x,z) => P551(x,z)`; evidence: Q37134 P20 Q64
- #2 Roberto Rossellini (Q53003) → Rome (Q220) — score 0.411; 3 rule(s); best `P20(x,z) => P551(x,z)`; evidence: Q53003 P20 Q220
- #3 Jean-Baptiste Biot (Q58328) → Paris (Q90) — score 0.411; 3 rule(s); best `P20(x,z) => P551(x,z)`; evidence: Q58328 P20 Q90

**narrative location (P840)**
- #1 Gone with the Wind (Q2875) → Burbank (Q39561) — score 0.096; 1 rule(s); best `P161(x,y) & P20(y,z) => P840(x,z)`; evidence: Q2875 P161 Q287688; Q287688 P20 Q39561
- #2 Gone with the Wind (Q2875) → Woodland Hills (Q1337818) — score 0.096; 1 rule(s); best `P161(x,y) & P20(y,z) => P840(x,z)`; evidence: Q2875 P161 Q228904; Q228904 P20 Q1337818
- #3 The Manchurian Candidate (Q3589) → Manhattan (Q11299) — score 0.096; 1 rule(s); best `P161(x,y) & P20(y,z) => P840(x,z)`; evidence: Q3589 P161 Q51559; Q51559 P20 Q11299

**instrument (P1303)**
- #1 Sean Penn (Q44221) → guitar (Q6607) — score 0.417; 4 rule(s); best `P26(y,x) & P1303(y,z) => P1303(x,z)`; evidence: Q1744 P26 Q44221; Q1744 P1303 Q6607
- #2 Sean Penn (Q44221) → voice (Q17172850) — score 0.417; 4 rule(s); best `P26(y,x) & P1303(y,z) => P1303(x,z)`; evidence: Q1744 P26 Q44221; Q1744 P1303 Q17172850
- #3 Rohan Marley (Q1939373) → voice (Q17172850) — score 0.417; 4 rule(s); best `P26(y,x) & P1303(y,z) => P1303(x,z)`; evidence: Q214226 P26 Q1939373; Q214226 P1303 Q17172850

**languages spoken, written, or signed (P1412)**
- #1 Wilhelm I of Germany (Q150652) → German (Q188) — score 0.783; 6 rule(s); best `P20(x,y) & P37(y,z) => P1412(x,z)`; evidence: Q150652 P20 Q64; Q64 P37 Q188
- #2 Géza von Radványi (Q386394) → Hungarian (Q9067) — score 0.783; 6 rule(s); best `P20(x,y) & P37(y,z) => P1412(x,z)`; evidence: Q386394 P20 Q1781; Q1781 P37 Q9067
- #3 Alessandro Manzoni (Q1064) → Italian (Q652) — score 0.783; 5 rule(s); best `P20(x,y) & P37(y,z) => P1412(x,z)`; evidence: Q1064 P20 Q490; Q490 P37 Q652

**sibling (P3373)**
- #1 Napoleon (Q517) → Jérôme Bonaparte (Q151087) — score 0.957; 3 rule(s); best `P40(y,x) & P40(y,z) => P3373(x,z)`; evidence: Q151869 P40 Q517; Q151869 P40 Q151087
- #2 Napoleon (Q517) → Pauline Bonaparte (Q152785) — score 0.957; 3 rule(s); best `P40(y,x) & P40(y,z) => P3373(x,z)`; evidence: Q151869 P40 Q517; Q151869 P40 Q152785
- #3 Michael Jackson (Q2831) → La Toya Jackson (Q217427) — score 0.957; 3 rule(s); best `P40(y,x) & P40(y,z) => P3373(x,z)`; evidence: Q238402 P40 Q2831; Q238402 P40 Q217427

## Limitations

- Rule scores are training statistics, not calibrated probabilities; a high score is not proof that a triple is true.
- Scores of 8 couple-counted rules are per couple, the others per ordered pair; both are Wilson lower bounds on the same 0–1 scale.
- Hub entities (for example Q30) can generate many candidates; the cap keeps only the top 100 per relation.
- One round only: no prediction is used as evidence for another.
- The Phase 2 graph was read from its GraphML export (networkx/pyvis not available here); it is checked against train.txt.
- No validation or test scoring was done (Phase 6).
