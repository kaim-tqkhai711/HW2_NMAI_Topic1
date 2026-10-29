# FULL_RUN_SUMMARY (chunk 1-6)

**Nhãn: ô 9×9@0,1 s là "budget-noisy"** (mục 2): giữ nguyên dữ liệu, không dùng để khẳng định tuân thủ budget; một lần chạy lặp
với 6 worker (`results/main_9x9/full_w6_0.1/`, chunk 11) sẽ được so thứ hạng (Kendall tau, Elo từng agent).

Dữ liệu: `results/{ablation_ab,ablation_mcts,scaling,main_7x7,main_9x9}/full`, máy 22 logical CPU
(10 worker), chạy 28-29/10/2026. Chunk 7-10 (main_11x11, failure_mining, nodes_budget) **chưa chạy**.

**Quy ước kết luận.** CI Elo (bootstrap, neo Random = 0) rất rộng (±150-250) và các agent dùng chung điểm neo
nên CI chồng lấn dù hai agent cách nhau rõ ràng. Vì vậy mỗi kết luận ghi hai thứ: (i) CI Elo có chồng lấn không,
(ii) đối đầu trực tiếp: điểm số trên các ván giữa hai agent đó, CI Wilson 95 % có loại trừ 0,5 không.
**Kết luận được** = (ii) loại trừ 0,5 (ghi thêm nếu (i) cũng tách). **Chưa phân biệt được** = (ii) chứa 0,5.
Ván đối đầu dùng chung các thế khai cuộc nên đây là so sánh ghép cặp, nhưng kiểm định chưa hiệu chỉnh đa so sánh.

## 1. Kiểm tra dữ liệu

| run | ô (bàn @ budget) | ván thực tế / dự kiến | trùng id | ván lỗi / thiếu trường |
|---|---|---|---|---|
| ablation_ab | 9x5@0.5 | 840 / 840 | 0 | 0 |
| ablation_mcts | 9x5@0.5 | 1.800 / 1.800 | 0 | 0 |
| scaling | 7x4, 9x5, 11x5 @0.5 | 240 / 240 mỗi ô | 0 | 0 |
| main_7x7 | 7x4@0.5 | 4.800 / 4.800 | 0 | 0 |
| main_9x9 | 9x5@0.1, @0.5, @1 | 12.000 / 12.000 mỗi ô (36.000) | 0 | 0 |

Mọi cặp agent đủ đúng `games_per_pair` ván (kiểm từng cặp); không có `result` ngoài {-1,0,1}, không ván rỗng,
không nước đi thiếu `wall_s`/`nodes`/`stat_time_s`. `puzzles.csv` (30 thế x 16 agent), `ab_depth.csv`,
`nodes_vs_depth.csv` có đủ.

## 2. Vi phạm budget (> 1,5 x budget; yêu cầu < 1 %)

Tính lại từ `wall_s` của từng nước (cùng quy tắc `experiments/violation_rates.py`); bảng đầy đủ ở phụ lục A1.

* **Đạt** ở 7x7@0.5 (tệ nhất 0,00 %), 9x9@0.5 (tệ nhất 0,03 %: `mcts_ab_tac`, 4/11.469 nước, max 3,30x;
  `ab_order_id_tt` 0,02 %), 9x9@1.0 (tệ nhất 0,01 %: `mcts_ab` 1 nước, 1,84x), ablation_ab và ablation_mcts
  (0,00 %), scaling (0,34 %: `mcts_ab` 7x4, 1/293 nước).
* **KHÔNG đạt ở 9x9@0.1: 13/15 agent tìm kiếm vượt 1 %** (chỉ `ab_plain` 0,08 % và `backtracking_d2` 0,02 % đạt; `random` 0 %):

| agent | vi phạm % | max |
|---|---|---|
| mcts_ab_tac | 6,79 | 8,34x |
| mcts_heuristic_tac | 6,43 | 4,14x |
| mcts_rave_tac | 6,35 | 3,00x |
| mcts_ab | 5,96 | 6,90x |
| mcts_rave | 5,38 | 6,92x |
| mcts_heuristic | 4,80 | 3,78x |
| mcts_eval_tac | 2,93 | 2,40x |
| mcts_eval | 2,36 | 4,26x |
| ab_order | 2,11 | 2,65x |
| mcts_random | 1,81 | 2,49x |
| ab_full | 1,57 | 2,26x |
| ab_order_id_tt | 1,17 | 2,40x |
| ab_full_timed | 1,16 | 2,50x |

  Chẩn đoán: (a) vượt budget là **tuyệt đối**, không theo tỉ lệ: nhóm nước vượt > 50 ms có trung vị vượt 56-77 ms ở mọi
  agent (AB lẫn MCTS), nên ở 0,1 s thành ~1,6x còn ở 0,5 s chỉ ~1,1x. Overshoot tuyệt đối của mọi nước đi (ms, wall - 0,1 s) ở 9x9@0,1:

| agent | số nước | trung vị | p95 | max | % nước vượt > 50 ms |
|---|---|---|---|---|---|
| ab_full | 13,205 | +6 | +38 | 126 | 1.6 |
| ab_full_timed | 13,379 | +6 | +34 | 150 | 1.2 |
| ab_order | 14,634 | +6 | +39 | 165 | 2.1 |
| ab_order_id_tt | 13,327 | +5 | +33 | 140 | 1.2 |
| ab_plain | 14,463 | +3 | +10 | 74 | 0.1 |
| backtracking_d2 | 15,700 | -52 | +4 | 74 | 0.0 |
| mcts_ab | 14,273 | +12 | +53 | 590 | 6.0 |
| mcts_ab_tac | 15,847 | +11 | +58 | 734 | 6.8 |
| mcts_eval | 8,984 | +14 | +39 | 326 | 2.4 |
| mcts_eval_tac | 9,003 | +13 | +43 | 140 | 2.9 |
| mcts_heuristic | 14,424 | +7 | +50 | 278 | 4.8 |
| mcts_heuristic_tac | 14,866 | +5 | +55 | 314 | 6.4 |
| mcts_random | 13,456 | +15 | +40 | 149 | 1.8 |
| mcts_rave | 12,465 | +6 | +51 | 592 | 5.4 |
| mcts_rave_tac | 12,277 | +3 | +54 | 200 | 6.3 |

  (`backtracking_d2` âm vì dừng sớm.) Trung vị chỉ +3...+15 ms; vi phạm đến từ phần đuôi (p95 +33...+58 ms, max tới 734 ms ở hybrid AB-lá);
  (b) đồng hồ trong chính agent (`stat_time_s`) cũng > 0,15 s ở 6.572 /
  6.585 nước vi phạm, tức không phải độ trễ của harness; (c) thử riêng trên 60 thế 9x9 @0,1 s: `ab_order_id_tt`
  chạy một mình 0,0 % vi phạm, chạy 10 tiến trình song song 10,8 %; `mcts_heuristic` 10,0 % một mình và 9,3 %
  song song. Kết luận thận trọng: nhiễu lập lịch khi 10 worker chạy trên CPU lai + độ thô của kiểm tra đồng hồ
  của MCTS cộng lại; **chưa tách được hai nguyên nhân**. Hệ quả: Elo ở ô 0,1 s có agent được "tặng" thêm
  ~50-60 ms (+50 % budget) và không nên dùng để khẳng định tuân thủ budget. Ba hướng (cần bạn chọn, tôi chưa làm):
  1. giữ dữ liệu, ghi rõ ô 0,1 s là "budget-noisy" trong báo cáo (không tốn thời gian);
  2. chạy lại riêng 9x5@0.1 với 6 worker để kiểm tra giả thuyết lập lịch (~0,8 h theo mô hình, vì 0,48 h ở 10 worker);
  3. đổi quy tắc vi phạm thành `wall > 1,5 x budget + 0,06 s` (chỉ là diễn đạt lại, không làm tăng tuân thủ thực).

## 3. Nguồn dữ liệu của hình/bảng/failure_cases

* Hình lúc 09:36:09-18 và bảng 09:36:19, sau ván cuối (09:32:19), `summary.csv` (09:33:48) và `puzzles.csv`
  (09:36:07) của main_9x9. `experiments/plots.py` đọc `latest_runs` = thư mục `full` cho ablation_ab, ablation_mcts,
  scaling, main_7x7, main_9x9. Bảng `elo_ranking.tex` ghi 600 ván/agent (7x7) và 1.500 ván/agent (9x9, ô 1 s).
  Cột "games" của bảng là chỗ duy nhất ghi số ván; hình không ghi.
* **Ngoại lệ 1: `budget_modes` KHÔNG phải FULL.** Nó dùng `results/nodes_budget/20261019-053442` (264 ván,
  chạy quick trước khi sửa đồng hồ). Sẽ được thay khi chunk 9 xong (thư mục `full` xếp sau trong `latest_runs`).
* **Ngoại lệ 2: `failure_cases.md` bản cũ (09:36:26) quét 47.424 ván, trong đó 3.264 ván không phải FULL**
  (pilot_main/pilot2 2.400, pilot_11x11 360, failure_mining cũ 240, nodes_budget quick 264) và 3 ví dụ MCTS
  lấy từ failure_mining cũ. Đã sửa (`experiments/failure_cases.py`: chỉ quét thư mục `full`, cờ `--all-runs`
  để quét lại tất cả) và sinh lại: **44.160 ván, đều FULL**.
* Còn lại: `solve.tex` đến từ `results/solve.csv` (19/10), không thuộc các chunk này.

## 4. Tóm tắt sơ bộ

### 4.1 Elo (đầy đủ có CI ở phụ lục A2, A3)

Thứ tự nhóm giống nhau ở cả 4 ô: **nhóm AB có sắp xếp nước đi** (ab_order, ab_order_id_tt, ab_full, ab_full_timed)
> các biến thể MCTS (đứng đầu là `mcts_eval_tac`) > `backtracking_d2` > `ab_plain` > Random. Thứ tự bên trong nhóm
MCTS khác giữa 7x7 và 9x9 (ở 9x9: eval_tac > eval > rave_tac > rave > heuristic_tac > random_rollout > heuristic > hybrid AB-lá;
ở 7x7 `mcts_eval` chỉ đứng thứ 4 trong MCTS và `mcts_rave` thứ 6).

| ô | AB tốt nhất (Elo [CI]) | MCTS tốt nhất (Elo [CI]) | CI Elo | đối đầu ab_order vs mcts_eval_tac |
|---|---|---|---|---|
| 7x7@0.5 | ab_order 1742 [1566, 2038] | mcts_eval_tac 1646 [1475, 1914] | chồng lấn | 0,65 [0,50, 0,78] chưa phân biệt (với ab_order_id_tt: 0,725 [0,57, 0,84] **tách**; ab_full_timed 0,65 [0,50, 0,78]) |
| 9x9@0.1 | ab_order_id_tt 2659 [2539, 2801] | mcts_eval_tac 1638 [1524, 1773] | **tách** | 1,00 [0,96, 1,00] **tách** |
| 9x9@0.5 | ab_order 2376 [2209, 2641] | mcts_eval_tac 1908 [1745, 2176] | **tách** (sát: 2209 > 2176) | 0,94 [0,88, 0,97] **tách** |
| 9x9@1.0 | ab_order 2182 [2058, 2387] | mcts_eval_tac 1850 [1722, 2045] | **tách** (sát: 2058 > 2045) | 0,92 [0,85, 0,96] **tách** |

* Trong nhóm AB (4 biến thể có order): mọi cặp **chưa phân biệt được** ở mọi ô (xem 4.2).
* Xu hướng theo budget ở 9x9: khoảng cách AB-MCTS **thu hẹp khi budget tăng**: điểm của `ab_full_timed` trước
  `mcts_eval_tac` là 1,00 → 0,885 → 0,84 (CI [0,96, 1,00] so với [0,76, 0,90]: tách giữa 0,1 s và 1 s).
  Cùng cặp ab_order vs mcts_eval_tac: 1,00 → 0,94 → 0,92 (cùng xu hướng, nhưng CI [0,96, 1,00] và [0,85, 0,96] chỉ tách giữa 0,1 s
  và 1 s). Elo tuyệt đối **không so sánh được giữa các budget** (mỗi ô neo riêng vào Random, và đối thủ MCTS mạnh lên
  làm Elo của AB tụt 2648 → 2322 → 2130), nên xu hướng được đọc từ điểm đối đầu cố định cặp.
* Ô 0,1 s bị nhiễu budget (mục 2).
* Lai ghép: `mcts_eval` (lá = đánh giá tĩnh) là MCTS mạnh nhất; `mcts_ab` (lá = AB depth 2) **yếu hơn** `mcts_heuristic`
  ở 9x9 (đối đầu 0,29-0,30 ở cả 3 budget, CI [0,21, 0,39] **tách**) vì chỉ 150-170 mô phỏng/s.
* Puzzle (9x9, 0,5 s, 30 thế): AB có order 1,00, `ab_plain` 0,10, `backtracking_d2` 0,67, MCTS không TAC 0,83-0,87,
  mọi MCTS TAC 1,00 (phụ lục A4).

### 4.2 Ablation AB (9x5@0.5, 40 ván/cặp; và main_9x9 @0.1/0.5/1.0, 100 ván/cặp)

Số nút ở depth 4 trên 3 thế giữa ván 9x9 (đếm tất định, n = 3 thế, mô tả không có CI):
PLAIN 1.064.799 nút / 33,5 s → ORDER 16.900 / 1,5 s (63 lần ít hơn) → +ID 22.339 (+32 %) → +TT 18.959 (TT hit
1.584) → FULL (radius 2 + killer) 9.461 (-50 %). Trên 7x4 `nodes_vs_depth`: ab_plain chạm trần 60 s ở depth 5, ab_order đến depth 6 trong 0,45 s
(chú ý: thế QUIET_74 có nước thắng, nên các cấu hình có TT/ID dừng sớm và đường số nút đi ngang từ depth 4).

| thành phần | đối đầu (điểm của vế trái) | 9x5@0.5 ablation (40 ván) | main_9x9 0.1 / 0.5 / 1.0 (100 ván) | kết luận |
|---|---|---|---|---|
| ordering | ab_order vs ab_plain | 1,00 [0,91, 1,00] | 1,00 [0,96, 1,00] cả 3 | **kết luận được** (CI Elo cũng tách) |
| ID | ab_order_id vs ab_order | 0,55 [0,40, 0,69] | (không có ab_order_id trong main) | chưa phân biệt được |
| TT | ab_order_id_tt vs ab_order_id | 0,525 [0,38, 0,67] | - | chưa phân biệt được |
| ID+TT | ab_order_id_tt vs ab_order | 0,49 [0,34, 0,64] | 0,51 / 0,47 / 0,46 (CI [0,41, 0,61], [0,38, 0,57], [0,37, 0,56]) | chưa phân biệt được |
| radius 2 + killer | ab_full vs ab_order_id_tt | 0,45 [0,31, 0,60] | 0,46 / 0,44 / 0,455 (gộp 300 ván: 0,452 [0,396, 0,508]) | chưa phân biệt được (gộp sát 0,5, thăm dò) |
| depth tối đa 10 vs 4 | ab_full_timed vs ab_full | 0,525 [0,38, 0,67] | 0,47 / 0,55 / 0,54 (gộp 0,5+1: 0,545 [0,48, 0,61]) | chưa phân biệt được |

* **Lợi ích của ID/TT có tăng theo budget không? Không thấy.** Điểm ID+TT trước ab_order: 0,51 → 0,47 → 0,46
  (đi xuống nhẹ, mọi CI chứa 0,5 và chồng nhau). Chỉ riêng ordering là đóng góp chắc chắn về sức mạnh; ID, TT,
  radius chỉ làm giảm số nút, không đổi sức mạnh trong khả năng đo của 100 ván/ô.
* Lưu ý để diễn giải: ở 9x9 các AB có ordering **hết giờ ở 52-86 % số nước** (`ab_plain` ~100 %) và chỉ đạt depth 2 (68 % nước ở 0,1 s) hay depth 3
  (66 % ở 1 s); ab_order (không ID) hết giờ 52-77 % và khi đó phải chơi nước dự phòng theo điểm cục bộ.
  Việc ID thay nước dự phòng bằng kết quả depth 2-3 mà không tăng điểm cho thấy nước dự phòng đã gần bằng depth 2-3
  với dàn đối thủ này. Cần giải thích như vậy trong báo cáo thay vì nói "ID không có tác dụng".

### 4.3 Ablation MCTS (9x5@0.5, 40 ván/cặp, nền = `uct_c1.414`, heuristic rollout)

| yếu tố | đối đầu | điểm | CI Elo | kết luận |
|---|---|---|---|---|
| c_uct | c0.5 vs c1.414 / c1.0 vs c1.414 / c2.0 vs c1.414 | 0,60 / 0,475 / 0,425 | chồng lấn | chưa phân biệt (cả c0.5 vs c2.0: 0,575 [0,42, 0,72]) |
| rollout | uct_c1.414 (heuristic) vs random_rollout | 0,50 [0,35, 0,65] | chồng lấn | chưa phân biệt (main 9x9: heuristic vs random 0,46-0,49 cũng chưa phân biệt, riêng 0,1 s: 0,63 **tách**) |
| RAVE | rave vs uct_c1.414 | 0,675 [0,52, 0,80] | chồng lấn | **kết luận được theo đối đầu** (main 9x9: rave vs heuristic 0,61 / 0,72 / 0,72, đều tách) |
| TAC | heuristic_tac vs uct_c1.414 | 0,85 [0,71, 0,93] | chồng lấn | **kết luận được** (main 9x9: 0,88 / 0,86 / 0,82) |
| TAC trên RAVE | rave_tac vs rave | 0,625 [0,47, 0,76] | chồng lấn | chưa phân biệt (main 9x9: 0,66 / 0,62 tách, 0,58 không) |
| tái dùng cây | no_reuse vs uct_c1.414 | 0,525 [0,38, 0,67] | chồng lấn | chưa phân biệt |

* TAC lợi nhiều nhất cho MCTS thuần/RAVE ở ngân sách ngắn và giảm khi budget tăng đối với lai AB: `mcts_ab_tac` vs
  `mcts_ab` 0,70 (0,1 s, tách) → 0,57 → 0,51 (chưa phân biệt).
* RAVE **đảo chiều theo kích thước bàn**: 9x9 giúp (0,72), 7x7 gây hại (`mcts_rave` vs `mcts_heuristic` = 0,325
  [0,20, 0,48], tách) → nên báo cáo là đặc trưng bàn, không phải "RAVE tốt".
* CI Elo của cả 10 biến thể ablation chồng lấn nhau; thứ tự Elo: rave_tac 1265 > heuristic_tac 1128 > rave 1099 >
  c0.5 964 > random_rollout 922 > c1.414 905 > no_reuse 900 > c1.0 893 > c2.0 873.

### 4.4 Scaling (0.5 s, 40 ván/cặp)

| bàn | ab_full_timed vs mcts_rave | mcts_rave vs mcts_ab | Elo (AB / rave / mcts_ab) |
|---|---|---|---|
| 7x4 | 0,725 [0,57, 0,84] | 0,525 [0,38, 0,67] (chưa phân biệt) | 945 / 776 / 752 |
| 9x5 | 0,975 [0,87, 1,00] | 0,85 [0,71, 0,93] | 1378 / 910 / 651 |
| 11x5 | 0,975 [0,87, 1,00] | 0,875 [0,74, 0,95] | 1615 / 978 / 636 |

* AB thắng MCTS rõ hơn khi bàn lớn: 7x4 → 9x5 **kết luận được** (CI tách: [0,57, 0,84] và [0,87, 1,00]); 9x5 → 11x5 không đổi.
* Hybrid `mcts_ab` kém dần: tốc độ 577 → 183 → 118 mô phỏng/s; so với `mcts_rave` từ ngang (7x4) thành thua rõ (9x5, 11x5).
* Elo gốc có CI rất rộng (vd AB 11x5 [1318, 2482]); xu hướng đọc từ đối đầu.

### 4.5 Vi phạm budget của mcts_ab / mcts_ab_tac trước/sau sửa đồng hồ (0,5 s; % nước > 1,5x, max)

| agent, bàn | pilot (trước sửa) | pilot2 (sau sửa) | full |
|---|---|---|---|
| mcts_ab 7x7 | 12,26 % (2,18x) | 0,00 % (1,18x) | 0,00 % (1,45x, 1.460 nước) |
| mcts_ab 9x9 | 67,73 % (7,96x) | 0,00 % (1,23x) | 0,00 % (1,37x, 10.595 nước) |
| mcts_ab_tac 7x7 | 12,87 % (2,18x) | 0,27 % (1,51x) | 0,00 % (1,41x, 1.543 nước) |
| mcts_ab_tac 9x9 | 70,18 % (7,88x) | 0,09 % (1,52x) | 0,03 % (3,30x, 4/11.469 nước) |

Bản sửa đồng hồ **giữ được trong full run ở 0,5 s và 1 s** (cả hai < 0,05 %). Ở 0,1 s thì không (mục 2), nhưng
đó là vi phạm tuyệt đối ~60 ms của mọi agent, không riêng hybrid; hybrid chỉ cao nhất (6-7 %) vì mô phỏng chậm
nhất (một mô phỏng AB-lá ~5-10 ms).

## 5. Failure cases (`results/failure_cases.md`, 44.160 ván FULL)

* **MCTS-miss: 3 ví dụ** (đã đủ giới hạn 3; tần suất thực: mẫu ngẫu nhiên 400 trong 24.699 ván MCTS thua cho 26 ca,
  ≈ 6,5 %, nên dữ liệu rất dồi dào).
* **AB-fail: 3 ví dụ** (thấy được sau sửa lỗi, trước đó chỉ 2). Nguyên nhân bản cũ chỉ ra 2 là **trần `scan=400`
  ván thua đầu tiên theo thứ tự file**, không phải thiếu dữ liệu: quét hết 7.192 ván thua của AB cho 38 ván ứng viên.
  **Cả 38 đều là `ab_plain`** (23 ở 9x5@0.1, 9 ở @0.5, 4 ở @1, 2 ở 7x4@0.5); không có ca nào cho
  ab_order/ID/TT/full trong 7.192 ván: tức "AB thua khi đánh giá của chính nó báo thắng" chỉ xảy ra với bản
  depth 4 không hoàn tất (không ordering). Vì vậy **không cần tăng failure_mining** cho số lượng (chunk 8 chạy
  < 1 phút nếu muốn thêm ván 7x4@0.1 và cũng không chắc có ca của AB mạnh). Nếu muốn ví dụ từ AB mạnh,
  cần hạ ngưỡng `margin_factor` (hiện 10^(k-1)): thay đổi nhỏ trong `failure_cases.py`, chưa làm.

## 6. Histogram nodes/s (9x9@0.5; `results/figures/nps_hist_9x9_0.5.{png,pdf}`)

Chọn `ab_order_id_tt`, `mcts_eval`, `mcts_random`; chỉ lấy 3 nước đầu của mỗi agent (cùng cỡ bàn; gộp mọi nước thì
phân bố bị trộn bởi giai đoạn ván, vd `mcts_rave` toàn ván rộng lệch phải chủ yếu do độ dài rollout) và nước chạy
≥ 0,25 s.

| agent | n | p5 / p50 / p95 nodes/s | hình dạng |
|---|---|---|---|
| ab_order_id_tt | 4.360 | 5.276 / 11.447 / 16.469 | đỉnh chính ~12-13k, **vai trái** 6-9k (lệch trái, hệ số ≈ 1,6-2 so với đỉnh) |
| mcts_eval | 4.491 | 1.391 / 2.397 / 3.540 | một đỉnh, p95/p5 = 2,5 |
| mcts_random | 4.465 | 848 / 1.399 / 2.127 | đỉnh rộng, phẳng ở 1,1-1,6k, p95/p5 = 2,5 |

Không có phân bố hai đỉnh rõ ràng (kiểm bằng đỉnh của histogram đã làm mịn; phép tách 2-means và thống kê Ashman D
~2,7 **không** dùng được vì 2-means cho D ≈ 2,65 cả với phân phối chuẩn một đỉnh). Vì vậy ghi vào Limitations ở dạng
thận trọng: thông lượng thay đổi trong khoảng p95/p5 ≈ 2,5-3,1 trong cùng một thế; `ab_order_id_tt` có vai chậm hơn
đỉnh chính ≈ 1,6-2 lần, phù hợp với nhưng **không chứng minh** hiệu ứng lõi P/E của CPU lai (Intel Core Ultra,
22 luồng); không ghim affinity. Hệ quả: một nước đi cùng budget có thể được tính trên tốc độ chênh tới ~2x giữa
hai ván, nhiễu này nằm trong CI đã báo.

## 7. Giới hạn bổ sung (đưa vào báo cáo)

1. Ô 9x9@0.1 vi phạm budget (mục 2); Elo ở ô này chỉ mang tính tham khảo.
2. `budget_modes` hiện từ dữ liệu quick, sẽ thay sau chunk 9.
3. Mọi AB đều giới hạn depth 4 (trừ `ab_full_timed`) và hết giờ phần lớn nước ở 9x9 (mục 4.2); kết luận về ID/TT/radius là về
   sức mạnh trong khung này.
4. So sánh nhiều cặp không hiệu chỉnh (Bonferroni); các "kết luận được" sát biên (CI chạm 0,5) nên đọc là gợi ý.
5. CI Elo neo Random bảo thủ; xem quy ước ở đầu file.

---

## Phụ lục (sinh bằng script từ `summary.csv`, `games.jsonl`)

### A1. Over-budget moves (wall > 1.5 x budget): rate % (max wall/budget) per agent and cell

| agent | 7x7 @0.5 | 9x9 @0.1 | 9x9 @0.5 | 9x9 @1.0 |
|---|---|---|---|---|
| ab_full | 0.00 (1.21x) | **1.57** (2.26x) | 0.00 (1.18x) | 0.00 (1.08x) |
| ab_full_timed | 0.00 (1.14x) | **1.16** (2.50x) | 0.00 (1.29x) | 0.00 (1.09x) |
| ab_order | 0.00 (1.15x) | **2.11** (2.65x) | 0.00 (1.20x) | 0.00 (1.09x) |
| ab_order_id_tt | 0.00 (1.11x) | **1.17** (2.40x) | 0.02 (1.69x) | 0.00 (1.10x) |
| ab_plain | 0.00 (1.14x) | 0.08 (1.74x) | 0.00 (1.26x) | 0.00 (1.04x) |
| backtracking_d2 | 0.00 (0.21x) | 0.02 (1.74x) | 0.00 (1.03x) | 0.00 (0.27x) |
| mcts_ab | 0.00 (1.45x) | **5.96** (6.90x) | 0.00 (1.37x) | 0.01 (1.84x) |
| mcts_ab_tac | 0.00 (1.41x) | **6.79** (8.34x) | 0.03 (3.30x) | 0.00 (1.12x) |
| mcts_eval | 0.00 (1.21x) | **2.36** (4.26x) | 0.00 (1.21x) | 0.00 (1.10x) |
| mcts_eval_tac | 0.00 (1.20x) | **2.93** (2.40x) | 0.00 (1.33x) | 0.00 (1.11x) |
| mcts_heuristic | 0.00 (1.25x) | **4.80** (3.78x) | 0.00 (1.31x) | 0.00 (1.16x) |
| mcts_heuristic_tac | 0.00 (1.23x) | **6.43** (4.14x) | 0.00 (1.29x) | 0.00 (1.12x) |
| mcts_random | 0.00 (1.21x) | **1.81** (2.49x) | 0.00 (1.28x) | 0.00 (1.11x) |
| mcts_rave | 0.00 (1.26x) | **5.38** (6.92x) | 0.00 (1.30x) | 0.00 (1.12x) |
| mcts_rave_tac | 0.00 (1.29x) | **6.35** (3.00x) | 0.00 (1.33x) | 0.00 (1.12x) |
| random | 0.00 (0.01x) | 0.00 (0.20x) | 0.00 (0.02x) | 0.00 (0.00x) |

Bold = at or above the 1 % requirement.

Other runs (single cell each): ablation_ab 9x5@0.5 worst 0.00 %; ablation_mcts 9x5@0.5 worst 0.00 % (max 1.46x); scaling worst 0.34 % (`mcts_ab` 7x4: 1 of 293 moves, 1.56x).

### A2. Elo, main_7x7 (40 games per pair, 600 per agent; Random = 0)

| agent | Elo @0.5 s [95 % CI] (score) |
|---|---|
| ab_order | 1742 [1566, 2038] (0.77) |
| ab_full_timed | 1739 [1577, 2012] (0.76) |
| ab_order_id_tt | 1739 [1555, 2022] (0.76) |
| ab_full | 1722 [1546, 2001] (0.75) |
| mcts_eval_tac | 1646 [1475, 1914] (0.67) |
| mcts_heuristic_tac | 1583 [1407, 1867] (0.59) |
| mcts_rave_tac | 1571 [1395, 1851] (0.58) |
| mcts_eval | 1549 [1377, 1840] (0.56) |
| mcts_heuristic | 1527 [1334, 1818] (0.53) |
| mcts_rave | 1499 [1322, 1785] (0.50) |
| mcts_ab_tac | 1473 [1275, 1756] (0.47) |
| mcts_ab | 1447 [1281, 1738] (0.45) |
| mcts_random | 1406 [1211, 1690] (0.41) |
| backtracking_d2 | 632 [471, 880] (0.13) |
| ab_plain | 251 [134, 422] (0.06) |
| random | 0 [0, 0] (0.01) |

### A3. Elo, main_9x9 (100 games per pair, 1,500 per agent; Random = 0 in each cell)

| agent | Elo @0.1 s [95 % CI] (score) | Elo @0.5 s [95 % CI] (score) | Elo @1.0 s [95 % CI] (score) |
|---|---|---|---|
| ab_order | 2650 [2537, 2788] (0.90) | 2376 [2209, 2641] (0.90) | 2182 [2058, 2387] (0.90) |
| ab_order_id_tt | 2659 [2539, 2801] (0.90) | 2351 [2188, 2634] (0.89) | 2131 [1998, 2342] (0.87) |
| ab_full_timed | 2648 [2533, 2775] (0.90) | 2322 [2155, 2579] (0.88) | 2130 [2005, 2329] (0.87) |
| ab_full | 2651 [2538, 2784] (0.90) | 2310 [2156, 2560] (0.88) | 2126 [2002, 2327] (0.87) |
| mcts_eval_tac | 1638 [1524, 1773] (0.68) | 1908 [1745, 2176] (0.69) | 1850 [1722, 2045] (0.72) |
| mcts_eval | 1527 [1416, 1670] (0.64) | 1809 [1653, 2076] (0.65) | 1751 [1618, 1964] (0.67) |
| mcts_rave_tac | 1376 [1255, 1512] (0.56) | 1671 [1524, 1925] (0.57) | 1550 [1410, 1751] (0.55) |
| mcts_rave | 1190 [1085, 1317] (0.44) | 1572 [1427, 1815] (0.51) | 1448 [1323, 1655] (0.48) |
| mcts_heuristic_tac | 1255 [1137, 1401] (0.49) | 1523 [1375, 1775] (0.48) | 1430 [1297, 1638] (0.47) |
| mcts_random | 952 [838, 1078] (0.28) | 1347 [1201, 1603] (0.37) | 1311 [1179, 1516] (0.39) |
| mcts_heuristic | 999 [886, 1142] (0.31) | 1300 [1142, 1548] (0.34) | 1286 [1157, 1490] (0.37) |
| mcts_ab_tac | 1071 [968, 1205] (0.36) | 1249 [1101, 1501] (0.31) | 1210 [1079, 1410] (0.32) |
| mcts_ab | 877 [782, 1024] (0.24) | 1170 [1043, 1422] (0.26) | 1156 [1026, 1350] (0.29) |
| backtracking_d2 | 1002 [893, 1141] (0.32) | 1040 [899, 1284] (0.20) | 881 [744, 1086] (0.17) |
| ab_plain | 321 [246, 420] (0.07) | 328 [236, 433] (0.06) | 320 [240, 426] (0.06) |
| random | 0 [0, 0] (0.01) | 0 [0, 0] (0.01) | 0 [0, 0] (0.01) |

### A4. Puzzle accuracy (main_9x9, 0.5 s per puzzle, 30 puzzles)

| agent | win_in_1 | block | win_in_3 | all |
|---|---|---|---|---|
| random | 0.0 | 0.0 | 0.0 | 0.0 |
| backtracking_d2 | 1.0 | 1.0 | 0.0 | 0.6667 |
| ab_plain | 0.2 | 0.1 | 0.0 | 0.1 |
| ab_order | 1.0 | 1.0 | 1.0 | 1.0 |
| ab_order_id_tt | 1.0 | 1.0 | 1.0 | 1.0 |
| ab_full | 1.0 | 1.0 | 1.0 | 1.0 |
| ab_full_timed | 1.0 | 1.0 | 1.0 | 1.0 |
| mcts_random | 1.0 | 0.6 | 1.0 | 0.8667 |
| mcts_heuristic | 1.0 | 0.6 | 1.0 | 0.8667 |
| mcts_rave | 1.0 | 0.6 | 1.0 | 0.8667 |
| mcts_eval | 1.0 | 0.6 | 1.0 | 0.8667 |
| mcts_ab | 1.0 | 0.5 | 1.0 | 0.8333 |
| mcts_heuristic_tac | 1.0 | 1.0 | 1.0 | 1.0 |
| mcts_rave_tac | 1.0 | 1.0 | 1.0 | 1.0 |
| mcts_eval_tac | 1.0 | 1.0 | 1.0 | 1.0 |
| mcts_ab_tac | 1.0 | 1.0 | 1.0 | 1.0 |
