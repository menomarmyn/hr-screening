# Результаты eval

| Провайдер / модель | Требований | Точность вердикта | Spearman | Injection-safe | $/резюме | Задержка, мс |
|---|---|---|---|---|---|---|
| mock/heuristic-v1 | 24 | 75% | 0.952 | да | 0.0 | 1 |

## mock/heuristic-v1

| Кандидат | Балл | Вердикт | Ожидалось | Ранг / ожид. |
|---|---|---|---|---|
| 01_arman_sadykov.txt | 91.9 | strong ✓ | strong | 1 / 1 |
| 06_madina_zhaksylyk.txt | 73.0 | strong ✓ | strong | 2 / 2 |
| 02_dana_ismailova.txt | 71.6 | strong ✗ | maybe | 3 / 4 |
| 04_aigerim_nurlanova.txt | 62.2 | maybe ✓ | maybe | 4 / 3 |
| 08_ruslan_bekov.txt | 54.1 | maybe ✓ | maybe | 5 / 5 |
| 05_sergey_kim.txt | 54.1 | maybe ✗ | reject | 6 / 7 |
| 03_timur_ermekov.txt | 37.8 | reject ✓ | reject | 7 / 6 |
| 07_oleg_petrov.txt | 24.3 | reject ✓ | reject | 8 / 8 |
