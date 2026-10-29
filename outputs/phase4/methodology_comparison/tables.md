# Methodology comparison tables (experimental)

## Rule-set validation at (0.10, 10), without the six excluded rules

| Mode | Rules | TP | FP | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| one | 160 | 2,451 | 594 | 0.8049 | 0.2377 | 0.3671 |
| both | 160 | 2,451 | 594 | 0.8049 | 0.2377 | 0.3671 |
| ordered | 160 | 2,451 | 594 | 0.8049 | 0.2377 | 0.3671 |
| hybrid | 160 | 2,451 | 594 | 0.8049 | 0.2377 | 0.3671 |

## Set differences vs mode 'one'

- **both**: added ['P3373(x,y) & P3373(y,z) => P3373(x,z)']; removed ['P3373(x,y) & P3373(z,y) => P3373(x,z)']
- **ordered**: added ['P3373(x,y) & P3373(y,z) => P3373(x,z)']; removed ['P3373(x,y) & P3373(z,y) => P3373(x,z)']
- **hybrid**: added none; removed none

## Swap-invariant rules (selected in some mode, or PCA ≥ 0.05 in some mode)

| Rule | Recip. | Mode | Support | Body | PCA body | Conf | PCA | HC | Wilson | Status | In set |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| `P3373(z,x) => P3373(x,z)` | 0.876945 | one | 310 | 397 | 366 | 0.780856 | 0.846995 | 0.780856 | 0.806524 | selected  | True |
| `P3373(z,x) => P3373(x,z)` | 0.876945 | both | 310 | 397 | 366 | 0.780856 | 0.846995 | 1.0 | 0.806524 | selected  | True |
| `P3373(z,x) => P3373(x,z)` | 0.876945 | ordered | 620 | 707 | 676 | 0.876945 | 0.91716 | 0.876945 | 0.893949 | selected  | True |
| `P3373(z,x) => P3373(x,z)` | 0.876945 | hybrid | 310 | 397 | 366 | 0.780856 | 0.846995 | 0.780856 | 0.806524 | selected  | True |
| `P451(z,x) => P451(x,z)` | 0.804469 | one | 144 | 214 | 166 | 0.672897 | 0.86747 | 0.672897 | 0.807491 | selected  | True |
| `P451(z,x) => P451(x,z)` | 0.804469 | both | 144 | 214 | 166 | 0.672897 | 0.86747 | 1.0 | 0.807491 | selected  | True |
| `P451(z,x) => P451(x,z)` | 0.804469 | ordered | 288 | 358 | 310 | 0.804469 | 0.929032 | 0.804469 | 0.894891 | selected  | True |
| `P451(z,x) => P451(x,z)` | 0.804469 | hybrid | 144 | 214 | 166 | 0.672897 | 0.86747 | 0.672897 | 0.807491 | selected  | True |
| `P26(z,x) => P26(x,z)` | 0.867876 | one | 335 | 437 | 354 | 0.76659 | 0.946328 | 0.76659 | 0.917699 | selected  | True |
| `P26(z,x) => P26(x,z)` | 0.867876 | both | 335 | 437 | 354 | 0.76659 | 0.946328 | 1.0 | 0.917699 | selected  | True |
| `P26(z,x) => P26(x,z)` | 0.867876 | ordered | 670 | 772 | 689 | 0.867876 | 0.972424 | 0.867876 | 0.957333 | selected  | True |
| `P26(z,x) => P26(x,z)` | 0.867876 | hybrid | 335 | 437 | 354 | 0.76659 | 0.946328 | 0.76659 | 0.917699 | selected  | True |
| `P551(y,x) & P551(y,z) => P530(x,z)` | 0.878777 | one | 34 | 625 | 166 | 0.0544 | 0.204819 | 0.01078 | 0.150435 | rejected lift_below_min | False |
| `P551(y,x) & P551(y,z) => P530(x,z)` | 0.878777 | both | 27 | 625 | 166 | 0.0432 | 0.162651 | 0.010922 | 0.114256 | rejected lift_below_min | False |
| `P551(y,x) & P551(y,z) => P530(x,z)` | 0.878777 | ordered | 61 | 1250 | 235 | 0.0488 | 0.259574 | 0.010843 | 0.207707 | rejected lift_below_min | False |
| `P551(y,x) & P551(y,z) => P530(x,z)` | 0.878777 | hybrid | 34 | 625 | 166 | 0.0544 | 0.204819 | 0.01078 | 0.150435 | rejected lift_below_min | False |
| `P17(x,y) & P17(z,y) => P530(x,z)` | 0.878777 | one | 7 | 26049 | 169 | 0.000269 | 0.04142 | 0.002219 | 0.020206 | rejected head_coverage_below_min,pca_below_min,lift_below_min | False |
| `P17(x,y) & P17(z,y) => P530(x,z)` | 0.878777 | both | 6 | 26049 | 169 | 0.00023 | 0.035503 | 0.002427 | 0.016371 | rejected head_coverage_below_min,pca_below_min,lift_below_min | False |
| `P17(x,y) & P17(z,y) => P530(x,z)` | 0.878777 | ordered | 13 | 52098 | 215 | 0.00025 | 0.060465 | 0.002311 | 0.035673 | rejected head_coverage_below_min,lift_below_min | False |
| `P17(x,y) & P17(z,y) => P530(x,z)` | 0.878777 | hybrid | 7 | 26049 | 169 | 0.000269 | 0.04142 | 0.002219 | 0.020206 | rejected head_coverage_below_min,pca_below_min,lift_below_min | False |
| `P138(y,x) & P138(y,z) => P3373(x,z)` | 0.876945 | one | 10 | 11 | 10 | 0.909091 | 1.0 | 0.025189 | 0.72246 | rejected pca_body_below_min | False |
| `P138(y,x) & P138(y,z) => P3373(x,z)` | 0.876945 | both | 5 | 11 | 10 | 0.454545 | 0.5 | 0.016129 | 0.23659 | rejected pca_body_below_min | False |
| `P138(y,x) & P138(y,z) => P3373(x,z)` | 0.876945 | ordered | 15 | 22 | 20 | 0.681818 | 0.75 | 0.021216 | 0.531295 | selected  | False |
| `P138(y,x) & P138(y,z) => P3373(x,z)` | 0.876945 | hybrid | 10 | 11 | 10 | 0.909091 | 1.0 | 0.025189 | 0.72246 | rejected pca_body_below_min | False |
| `P361(x,y) & P361(z,y) => P530(x,z)` | 0.878777 | one | 147 | 599 | 503 | 0.245409 | 0.292247 | 0.046607 | 0.254195 | rejected no_gain_over_shorter | False |
| `P361(x,y) & P361(z,y) => P530(x,z)` | 0.878777 | both | 128 | 599 | 503 | 0.213689 | 0.254473 | 0.05178 | 0.218368 | rejected no_gain_over_shorter | False |
| `P361(x,y) & P361(z,y) => P530(x,z)` | 0.878777 | ordered | 275 | 1198 | 1006 | 0.229549 | 0.27336 | 0.04888 | 0.24672 | rejected no_gain_over_shorter | False |
| `P361(x,y) & P361(z,y) => P530(x,z)` | 0.878777 | hybrid | 147 | 599 | 503 | 0.245409 | 0.292247 | 0.046607 | 0.254195 | rejected no_gain_over_shorter | False |
| `P17(y,x) & P17(y,z) => P530(x,z)` | 0.878777 | one | 27 | 507 | 284 | 0.053254 | 0.09507 | 0.008561 | 0.066161 | rejected head_coverage_below_min,lift_below_min | False |
| `P17(y,x) & P17(y,z) => P530(x,z)` | 0.878777 | both | 22 | 507 | 284 | 0.043393 | 0.077465 | 0.0089 | 0.05171 | rejected head_coverage_below_min,lift_below_min | False |
| `P17(y,x) & P17(y,z) => P530(x,z)` | 0.878777 | ordered | 49 | 1014 | 356 | 0.048323 | 0.13764 | 0.00871 | 0.105702 | rejected head_coverage_below_min,lift_below_min | False |
| `P17(y,x) & P17(y,z) => P530(x,z)` | 0.878777 | hybrid | 27 | 507 | 284 | 0.053254 | 0.09507 | 0.008561 | 0.066161 | rejected head_coverage_below_min,lift_below_min | False |
| `P40(y,x) & P40(y,z) => P3373(x,z)` | 0.876945 | one | 127 | 128 | 128 | 0.992188 | 0.992188 | 0.319899 | 0.957073 | selected  | True |
| `P40(y,x) & P40(y,z) => P3373(x,z)` | 0.876945 | both | 91 | 128 | 128 | 0.710938 | 0.710938 | 0.293548 | 0.627165 | selected  | True |
| `P40(y,x) & P40(y,z) => P3373(x,z)` | 0.876945 | ordered | 218 | 256 | 252 | 0.851562 | 0.865079 | 0.308345 | 0.817376 | selected  | True |
| `P40(y,x) & P40(y,z) => P3373(x,z)` | 0.876945 | hybrid | 127 | 128 | 128 | 0.992188 | 0.992188 | 0.319899 | 0.957073 | selected  | True |
| `P361(x,y) & P361(z,y) => P3373(x,z)` | 0.876945 | one | 5 | 599 | 12 | 0.008347 | 0.416667 | 0.012594 | 0.193257 | rejected pca_body_below_min,lift_below_min | False |
| `P361(x,y) & P361(z,y) => P3373(x,z)` | 0.876945 | both | 4 | 599 | 12 | 0.008347 | 0.416667 | 0.012594 | 0.193257 | rejected support_below_min | False |
| `P361(x,y) & P361(z,y) => P3373(x,z)` | 0.876945 | ordered | 9 | 1198 | 17 | 0.007513 | 0.529412 | 0.01273 | 0.309629 | rejected pca_body_below_min,lift_below_min | False |
| `P361(x,y) & P361(z,y) => P3373(x,z)` | 0.876945 | hybrid | 5 | 599 | 12 | 0.008347 | 0.416667 | 0.012594 | 0.193257 | rejected pca_body_below_min,lift_below_min | False |
| `P17(y,x) & P17(y,z) => P17(x,z)` | 0.0 | one | 8 | 507 | 79 | 0.015779 | 0.101266 | 0.006803 | 0.052211 | rejected head_coverage_below_min,lift_below_min | False |
| `P17(y,x) & P17(y,z) => P17(x,z)` | 0.0 | both | 0 | 507 | 79 | 0.015779 | 0.101266 | 0.006803 | 0.052211 | rejected support_below_min | False |
| `P17(y,x) & P17(y,z) => P17(x,z)` | 0.0 | ordered | 8 | 1014 | 82 | 0.00789 | 0.097561 | 0.006803 | 0.050268 | rejected head_coverage_below_min,lift_below_min | False |
| `P17(y,x) & P17(y,z) => P17(x,z)` | 0.0 | hybrid | 8 | 1014 | 82 | 0.00789 | 0.097561 | 0.006803 | 0.050268 | rejected head_coverage_below_min,lift_below_min | False |
| `P495(y,x) & P495(y,z) => P530(x,z)` | 0.878777 | one | 169 | 230 | 230 | 0.734783 | 0.734783 | 0.053583 | 0.674213 | rejected no_gain_over_shorter | False |
| `P495(y,x) & P495(y,z) => P530(x,z)` | 0.878777 | both | 142 | 230 | 230 | 0.617391 | 0.617391 | 0.057443 | 0.553138 | rejected no_gain_over_shorter | False |
| `P495(y,x) & P495(y,z) => P530(x,z)` | 0.878777 | ordered | 311 | 460 | 458 | 0.676087 | 0.679039 | 0.055279 | 0.634946 | rejected no_gain_over_shorter | False |
| `P495(y,x) & P495(y,z) => P530(x,z)` | 0.878777 | hybrid | 169 | 230 | 230 | 0.734783 | 0.734783 | 0.053583 | 0.674213 | rejected no_gain_over_shorter | False |
| `P27(y,x) & P27(y,z) => P530(x,z)` | 0.878777 | one | 303 | 894 | 772 | 0.338926 | 0.392487 | 0.096068 | 0.358655 | selected  | True |
| `P27(y,x) & P27(y,z) => P530(x,z)` | 0.878777 | both | 246 | 894 | 772 | 0.275168 | 0.318653 | 0.099515 | 0.286751 | selected  | True |
| `P27(y,x) & P27(y,z) => P530(x,z)` | 0.878777 | ordered | 549 | 1788 | 1250 | 0.307047 | 0.4392 | 0.097583 | 0.411915 | selected  | True |
| `P27(y,x) & P27(y,z) => P530(x,z)` | 0.878777 | hybrid | 303 | 894 | 772 | 0.338926 | 0.392487 | 0.096068 | 0.358655 | selected  | True |
| `P3373(x,y) & P3373(z,y) => P3373(x,z)` | 0.876945 | one | 240 | 259 | 259 | 0.926641 | 0.926641 | 0.604534 | 0.888274 | selected  | True |
| `P3373(x,y) & P3373(z,y) => P3373(x,z)` | 0.876945 | both | 192 | 259 | 259 | 0.741313 | 0.741313 | 0.619355 | 0.684727 | rejected redundant_with | False |
| `P3373(x,y) & P3373(z,y) => P3373(x,z)` | 0.876945 | ordered | 432 | 518 | 518 | 0.833977 | 0.833977 | 0.611033 | 0.799497 | rejected redundant_with | False |
| `P3373(x,y) & P3373(z,y) => P3373(x,z)` | 0.876945 | hybrid | 240 | 259 | 259 | 0.926641 | 0.926641 | 0.604534 | 0.888274 | selected  | True |
| `P40(x,y) & P40(z,y) => P26(x,z)` | 0.867876 | one | 36 | 39 | 36 | 0.923077 | 1.0 | 0.08238 | 0.903578 | selected  | True |
| `P40(x,y) & P40(z,y) => P26(x,z)` | 0.867876 | both | 27 | 39 | 36 | 0.692308 | 0.75 | 0.080597 | 0.589292 | selected  | True |
| `P40(x,y) & P40(z,y) => P26(x,z)` | 0.867876 | ordered | 63 | 78 | 63 | 0.807692 | 1.0 | 0.081606 | 0.942527 | selected  | True |
| `P40(x,y) & P40(z,y) => P26(x,z)` | 0.867876 | hybrid | 36 | 39 | 36 | 0.923077 | 1.0 | 0.08238 | 0.903578 | selected  | True |
| `P737(x,y) & P737(z,y) => P737(x,z)` | 0.011586 | one | 210 | 3109 | 2497 | 0.067546 | 0.084101 | 0.15295 | 0.073843 | selected  | False |
| `P737(x,y) & P737(z,y) => P737(x,z)` | 0.011586 | both | 2 | 3109 | 2497 | 0.067546 | 0.084101 | 0.15295 | 0.073843 | rejected support_below_min | False |
| `P737(x,y) & P737(z,y) => P737(x,z)` | 0.011586 | ordered | 212 | 6218 | 3528 | 0.034095 | 0.060091 | 0.153512 | 0.052717 | selected  | False |
| `P737(x,y) & P737(z,y) => P737(x,z)` | 0.011586 | hybrid | 212 | 6218 | 3528 | 0.034095 | 0.060091 | 0.153512 | 0.052717 | selected  | False |
| `P27(y,x) & P27(y,z) => P131(x,z)` | 0.0 | one | 11 | 894 | 102 | 0.012304 | 0.107843 | 0.059783 | 0.061293 | rejected lift_below_min | False |
| `P27(y,x) & P27(y,z) => P131(x,z)` | 0.0 | both | 0 | 894 | 102 | 0.012304 | 0.107843 | 0.059783 | 0.061293 | rejected support_below_min | False |
| `P27(y,x) & P27(y,z) => P131(x,z)` | 0.0 | ordered | 11 | 1788 | 108 | 0.006152 | 0.101852 | 0.059783 | 0.057829 | rejected lift_below_min | False |
| `P27(y,x) & P27(y,z) => P131(x,z)` | 0.0 | hybrid | 11 | 1788 | 108 | 0.006152 | 0.101852 | 0.059783 | 0.057829 | rejected lift_below_min | False |
| `P463(x,y) & P463(z,y) => P530(x,z)` | 0.878777 | one | 2978 | 563329 | 21281 | 0.005286 | 0.139937 | 0.944198 | 0.135341 | rejected lift_below_min | False |
| `P463(x,y) & P463(z,y) => P530(x,z)` | 0.878777 | both | 2417 | 563329 | 21281 | 0.004291 | 0.113575 | 0.977751 | 0.109382 | rejected lift_below_min | False |
| `P463(x,y) & P463(z,y) => P530(x,z)` | 0.878777 | ordered | 5395 | 1126658 | 41814 | 0.004788 | 0.129024 | 0.958941 | 0.125845 | rejected lift_below_min | False |
| `P463(x,y) & P463(z,y) => P530(x,z)` | 0.878777 | hybrid | 2978 | 563329 | 21281 | 0.005286 | 0.139937 | 0.944198 | 0.135341 | rejected lift_below_min | False |
| `P37(x,y) & P37(z,y) => P112(x,z)` | 0.0 | one | 6 | 4812 | 112 | 0.001247 | 0.053571 | 0.098361 | 0.024781 | rejected lift_below_min | False |
| `P37(x,y) & P37(z,y) => P112(x,z)` | 0.0 | both | 0 | 4812 | 112 | 0.001247 | 0.053571 | 0.098361 | 0.024781 | rejected support_below_min | False |
| `P37(x,y) & P37(z,y) => P112(x,z)` | 0.0 | ordered | 6 | 9624 | 121 | 0.000623 | 0.049587 | 0.098361 | 0.022921 | rejected pca_below_min,lift_below_min | False |
| `P37(x,y) & P37(z,y) => P112(x,z)` | 0.0 | hybrid | 6 | 9624 | 121 | 0.000623 | 0.049587 | 0.098361 | 0.022921 | rejected pca_below_min,lift_below_min | False |
| `P530(x,y) & P530(z,y) => P530(x,z)` | 0.878777 | one | 3035 | 21116 | 21116 | 0.14373 | 0.14373 | 0.96227 | 0.139063 | rejected lift_below_min | False |
| `P530(x,y) & P530(z,y) => P530(x,z)` | 0.878777 | both | 2461 | 21116 | 21116 | 0.116547 | 0.116547 | 0.99555 | 0.112288 | rejected lift_below_min | False |
| `P530(x,y) & P530(z,y) => P530(x,z)` | 0.878777 | ordered | 5496 | 42232 | 42178 | 0.130138 | 0.130305 | 0.976893 | 0.127126 | rejected lift_below_min | False |
| `P530(x,y) & P530(z,y) => P530(x,z)` | 0.878777 | hybrid | 3035 | 21116 | 21116 | 0.14373 | 0.14373 | 0.96227 | 0.139063 | rejected lift_below_min | False |
| `P30(x,y) & P30(z,y) => P530(x,z)` | 0.878777 | one | 1109 | 15811 | 11343 | 0.070141 | 0.09777 | 0.351617 | 0.092439 | rejected lift_below_min | False |
| `P30(x,y) & P30(z,y) => P530(x,z)` | 0.878777 | both | 865 | 15811 | 11343 | 0.054709 | 0.076258 | 0.349919 | 0.071516 | rejected lift_below_min | False |
| `P30(x,y) & P30(z,y) => P530(x,z)` | 0.878777 | ordered | 1974 | 31622 | 16072 | 0.062425 | 0.122822 | 0.350871 | 0.117838 | rejected lift_below_min | False |
| `P30(x,y) & P30(z,y) => P530(x,z)` | 0.878777 | hybrid | 1109 | 15811 | 11343 | 0.070141 | 0.09777 | 0.351617 | 0.092439 | rejected lift_below_min | False |
| `P530(z,x) => P530(x,z)` | 0.878777 | one | 2472 | 3154 | 3152 | 0.783767 | 0.784264 | 0.783767 | 0.769562 | selected  | True |
| `P530(z,x) => P530(x,z)` | 0.878777 | both | 2472 | 3154 | 3152 | 0.783767 | 0.784264 | 1.0 | 0.769562 | selected  | True |
| `P530(z,x) => P530(x,z)` | 0.878777 | ordered | 4944 | 5626 | 5624 | 0.878777 | 0.87909 | 0.878777 | 0.870309 | selected  | True |
| `P530(z,x) => P530(x,z)` | 0.878777 | hybrid | 2472 | 3154 | 3152 | 0.783767 | 0.784264 | 0.783767 | 0.769562 | selected  | True |
| `P3373(y,x) & P3373(y,z) => P3373(x,z)` | 0.876945 | one | 248 | 268 | 268 | 0.925373 | 0.925373 | 0.624685 | 0.887549 | rejected redundant_with | False |
| `P3373(y,x) & P3373(y,z) => P3373(x,z)` | 0.876945 | both | 192 | 268 | 268 | 0.716418 | 0.716418 | 0.619355 | 0.65969 | rejected redundant_with | False |
| `P3373(y,x) & P3373(y,z) => P3373(x,z)` | 0.876945 | ordered | 440 | 536 | 536 | 0.820896 | 0.820896 | 0.622348 | 0.786186 | rejected redundant_with | False |
| `P3373(y,x) & P3373(y,z) => P3373(x,z)` | 0.876945 | hybrid | 248 | 268 | 268 | 0.925373 | 0.925373 | 0.624685 | 0.887549 | rejected redundant_with | False |
| `P737(y,x) & P737(y,z) => P737(x,z)` | 0.011586 | one | 207 | 3494 | 3494 | 0.059244 | 0.059244 | 0.150765 | 0.05189 | selected  | False |
| `P737(y,x) & P737(y,z) => P737(x,z)` | 0.011586 | both | 1 | 3494 | 3494 | 0.059244 | 0.059244 | 0.150765 | 0.05189 | rejected support_below_min | False |
| `P737(y,x) & P737(y,z) => P737(x,z)` | 0.011586 | ordered | 208 | 6988 | 6988 | 0.029765 | 0.029765 | 0.150615 | 0.026032 | rejected pca_below_min | False |
| `P737(y,x) & P737(y,z) => P737(x,z)` | 0.011586 | hybrid | 208 | 6988 | 6988 | 0.029765 | 0.029765 | 0.150615 | 0.026032 | rejected pca_below_min | False |
| `P840(y,x) & P840(y,z) => P530(x,z)` | 0.878777 | one | 26 | 583 | 288 | 0.044597 | 0.090278 | 0.008244 | 0.062352 | rejected head_coverage_below_min,lift_below_min | False |
| `P840(y,x) & P840(y,z) => P530(x,z)` | 0.878777 | both | 26 | 583 | 288 | 0.044597 | 0.090278 | 0.010518 | 0.062352 | rejected lift_below_min | False |
| `P840(y,x) & P840(y,z) => P530(x,z)` | 0.878777 | ordered | 52 | 1166 | 365 | 0.044597 | 0.142466 | 0.009243 | 0.110325 | rejected head_coverage_below_min,lift_below_min | False |
| `P840(y,x) & P840(y,z) => P530(x,z)` | 0.878777 | hybrid | 26 | 583 | 288 | 0.044597 | 0.090278 | 0.008244 | 0.062352 | rejected head_coverage_below_min,lift_below_min | False |
| `P17(y,x) & P17(y,z) => P131(x,z)` | 0.0 | one | 8 | 507 | 98 | 0.015779 | 0.081633 | 0.043478 | 0.041944 | rejected lift_below_min | False |
| `P17(y,x) & P17(y,z) => P131(x,z)` | 0.0 | both | 0 | 507 | 98 | 0.015779 | 0.081633 | 0.043478 | 0.041944 | rejected support_below_min | False |
| `P17(y,x) & P17(y,z) => P131(x,z)` | 0.0 | ordered | 8 | 1014 | 101 | 0.00789 | 0.079208 | 0.043478 | 0.04068 | rejected lift_below_min | False |
| `P17(y,x) & P17(y,z) => P131(x,z)` | 0.0 | hybrid | 8 | 1014 | 101 | 0.00789 | 0.079208 | 0.043478 | 0.04068 | rejected lift_below_min | False |
| `P27(y,x) & P27(y,z) => P17(x,z)` | 0.0 | one | 12 | 894 | 85 | 0.013423 | 0.141176 | 0.010204 | 0.082642 | rejected lift_below_min | False |
| `P27(y,x) & P27(y,z) => P17(x,z)` | 0.0 | both | 0 | 894 | 85 | 0.013423 | 0.141176 | 0.010204 | 0.082642 | rejected support_below_min | False |
| `P27(y,x) & P27(y,z) => P17(x,z)` | 0.0 | ordered | 12 | 1788 | 87 | 0.006711 | 0.137931 | 0.010204 | 0.080697 | rejected lift_below_min | False |
| `P27(y,x) & P27(y,z) => P17(x,z)` | 0.0 | hybrid | 12 | 1788 | 87 | 0.006711 | 0.137931 | 0.010204 | 0.080697 | rejected lift_below_min | False |
| `P530(y,x) & P530(y,z) => P530(x,z)` | 0.878777 | one | 3137 | 21870 | 21870 | 0.143439 | 0.143439 | 0.99461 | 0.138855 | rejected lift_below_min | False |
| `P530(y,x) & P530(y,z) => P530(x,z)` | 0.878777 | both | 2464 | 21870 | 21870 | 0.112666 | 0.112666 | 0.996764 | 0.108543 | rejected lift_below_min | False |
| `P530(y,x) & P530(y,z) => P530(x,z)` | 0.878777 | ordered | 5601 | 43740 | 43740 | 0.128052 | 0.128052 | 0.995556 | 0.124953 | rejected lift_below_min | False |
| `P530(y,x) & P530(y,z) => P530(x,z)` | 0.878777 | hybrid | 3137 | 21870 | 21870 | 0.143439 | 0.143439 | 0.99461 | 0.138855 | rejected lift_below_min | False |
| `P37(x,y) & P37(z,y) => P530(x,z)` | 0.878777 | one | 421 | 4812 | 4258 | 0.08749 | 0.098873 | 0.133481 | 0.090265 | rejected lift_below_min | False |
| `P37(x,y) & P37(z,y) => P530(x,z)` | 0.878777 | both | 350 | 4812 | 4258 | 0.072735 | 0.082198 | 0.141586 | 0.07432 | rejected lift_below_min | False |
| `P37(x,y) & P37(z,y) => P530(x,z)` | 0.878777 | ordered | 771 | 9624 | 6875 | 0.080112 | 0.112145 | 0.137042 | 0.104902 | rejected lift_below_min | False |
| `P37(x,y) & P37(z,y) => P530(x,z)` | 0.878777 | hybrid | 421 | 4812 | 4258 | 0.08749 | 0.098873 | 0.133481 | 0.090265 | rejected lift_below_min | False |
| `P37(x,y) & P37(z,y) => P17(x,z)` | 0.0 | one | 93 | 4812 | 1637 | 0.019327 | 0.056811 | 0.079082 | 0.0466 | rejected lift_below_min | False |
| `P37(x,y) & P37(z,y) => P17(x,z)` | 0.0 | both | 0 | 4812 | 1637 | 0.019327 | 0.056811 | 0.079082 | 0.0466 | rejected support_below_min | False |
| `P37(x,y) & P37(z,y) => P17(x,z)` | 0.0 | ordered | 93 | 9624 | 1828 | 0.009663 | 0.050875 | 0.079082 | 0.04171 | rejected lift_below_min | False |
| `P37(x,y) & P37(z,y) => P17(x,z)` | 0.0 | hybrid | 93 | 9624 | 1828 | 0.009663 | 0.050875 | 0.079082 | 0.04171 | rejected lift_below_min | False |
| `P27(y,x) & P27(y,z) => P112(x,z)` | 0.0 | one | 5 | 894 | 100 | 0.005593 | 0.05 | 0.081967 | 0.021543 | rejected lift_below_min | False |
| `P27(y,x) & P27(y,z) => P112(x,z)` | 0.0 | both | 0 | 894 | 100 | 0.005593 | 0.05 | 0.081967 | 0.021543 | rejected support_below_min | False |
| `P27(y,x) & P27(y,z) => P112(x,z)` | 0.0 | ordered | 5 | 1788 | 108 | 0.002796 | 0.046296 | 0.081967 | 0.019935 | rejected pca_below_min,lift_below_min | False |
| `P27(y,x) & P27(y,z) => P112(x,z)` | 0.0 | hybrid | 5 | 1788 | 108 | 0.002796 | 0.046296 | 0.081967 | 0.019935 | rejected pca_below_min,lift_below_min | False |

## Sibling transitivity vs shared-sibling

```json
{
 "available": true,
 "P3373(x,y) & P3373(y,z) => P3373(x,z)": {
  "rule_id": "786021c91dba5ff9",
  "body_pairs": 526,
  "support_pairs": 440,
  "file_status": "rejected",
  "file_reasons": [
   "redundant_with:789b73c97cec8a95"
  ],
  "val_hits": 23,
  "val_neg_hits": 1,
  "val_hits_not_covered_by_other_proposed_rules": 0,
  "val_neg_hits_not_covered_by_other_proposed_rules": 1,
  "status_by_mode": {
   "one": "rejected",
   "both": "selected",
   "ordered": "selected",
   "hybrid": "rejected"
  },
  "reasons_by_mode": {
   "one": [
    "redundant_with:789b73c97cec8a95"
   ],
   "both": [],
   "ordered": [],
   "hybrid": [
    "redundant_with:789b73c97cec8a95"
   ]
  }
 },
 "P3373(x,y) & P3373(z,y) => P3373(x,z)": {
  "rule_id": "789b73c97cec8a95",
  "body_pairs": 518,
  "support_pairs": 432,
  "file_status": "selected",
  "file_reasons": [],
  "val_hits": 23,
  "val_neg_hits": 1,
  "val_hits_not_covered_by_other_proposed_rules": 0,
  "val_neg_hits_not_covered_by_other_proposed_rules": 1,
  "status_by_mode": {
   "one": "selected",
   "both": "rejected",
   "ordered": "rejected",
   "hybrid": "selected"
  },
  "reasons_by_mode": {
   "one": [],
   "both": [
    "redundant_with:786021c91dba5ff9"
   ],
   "ordered": [
    "redundant_with:786021c91dba5ff9"
   ],
   "hybrid": []
  }
 },
 "P3373(y,x) & P3373(y,z) => P3373(x,z)": {
  "rule_id": "a1fb07ef96915146",
  "body_pairs": 536,
  "support_pairs": 440,
  "file_status": "rejected",
  "file_reasons": [
   "redundant_with:789b73c97cec8a95"
  ],
  "val_hits": 23,
  "val_neg_hits": 1,
  "val_hits_not_covered_by_other_proposed_rules": 0,
  "val_neg_hits_not_covered_by_other_proposed_rules": 1,
  "status_by_mode": {
   "one": "rejected",
   "both": "rejected",
   "ordered": "rejected",
   "hybrid": "rejected"
  },
  "reasons_by_mode": {
   "one": [
    "redundant_with:789b73c97cec8a95"
   ],
   "both": [
    "redundant_with:786021c91dba5ff9"
   ],
   "ordered": [
    "redundant_with:786021c91dba5ff9"
   ],
   "hybrid": [
    "redundant_with:789b73c97cec8a95"
   ]
  }
 },
 "overlap": {
  "support_jaccard_T_S1": 0.963964,
  "support_jaccard_T_S2": 0.977528,
  "body_jaccard_T_S1": 0.969811,
  "support_only_T_vs_S1": 12,
  "support_only_S1_vs_T": 4,
  "body_only_T_vs_S1": 12,
  "body_only_S1_vs_T": 4,
  "val_hits_only_T_vs_S1": 0,
  "val_hits_only_S1_vs_T": 0,
  "val_neg_only_T_vs_S1": 0,
  "val_neg_only_S1_vs_T": 0,
  "proposed_set_plus_T": {
   "rules": 161,
   "tp": 2451,
   "fp": 594,
   "fn": 7859,
   "precision": 0.804926,
   "recall": 0.23773,
   "f1": 0.367054
  },
  "proposed_set": {
   "rules": 160,
   "tp": 2451,
   "fp": 594,
   "fn": 7859,
   "precision": 0.804926,
   "recall": 0.23773,
   "f1": 0.367054
  },
  "proposed_set_minus_S1": {
   "rules": 159,
   "tp": 2451,
   "fp": 593,
   "fn": 7859,
   "precision": 0.805191,
   "recall": 0.23773,
   "f1": 0.367081
  }
 }
}
```
