# FULL_RUN_SUMMARY (dữ liệu thực nghiệm đã chốt, chunk 1-11)

**Trạng thái: data freeze.** Mọi chunk đã chạy xong; không chạy lại thực nghiệm nào nếu không có yêu cầu mới.
Mục 8 = đối chứng 10 vs 6 worker ở ô 9x9@0,1 s; mục 9 = các so sánh bổ sung (11x11, thời gian vs node);
mục 10 = Findings cuối cùng; mục 11 = danh sách figure/bảng; mục 12 = Limitations (bản chốt); mục 13 = nén + đóng gói.
Ô 9×9@0,1 s vẫn là **budget-noisy** (mục 2, 8): dùng cho xếp hạng, không dùng để khẳng định tuân thủ budget.

Dữ liệu FULL: `results/{ablation_ab,ablation_mcts,scaling,main_7x7,main_9x9,main_11x11,failure_mining,nodes_budget}/full`
và bản lặp `results/main_9x9/full_w6_0.1` (chỉ dùng cho đối chứng). Máy 22 logical CPU (CPU lai), `--workers 10`
(chunk 11: 6 worker), chạy 28/10-01/11/2026.

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
| main_9x9/full_w6_0.1 (bản lặp, 6 worker) | 9x5@0.1 | 12.000 / 12.000 | 0 | 0 |
| main_11x11 | 11x5@0.5 | 3.600 / 3.600 (36 cặp x 100) | 0 | 0 |
| failure_mining | 7x4@0.1 | 240 / 240 (6 cặp x 40) | 0 | 0 |
| nodes_budget | 7x4@2000, 7x4@10000, 9x5@2000 | 9.100 / 9.100 mỗi ô (27.300) | 0 | 0 |

Kiểm lại ngày 01/11 bằng script riêng trên cả 9 thư mục: mọi cặp agent đủ đúng `games_per_pair` ván (kiểm từng cặp, từng ô); `config.yaml`
của từng run trùng `experiments/configs/*.yaml` (seed, boards, budgets, games_per_pair, agents, budget_mode); không dòng JSON hỏng;
không `game_id` trùng **trong** mọi run. Duy nhất `main_9x9/full` và `main_9x9/full_w6_0.1` chia sẻ 12.000 `game_id` của ô 0,1 s
**có chủ đích** (cùng seed/thế khai cuộc, đây là bản lặp; không bao giờ gộp vào cùng một phép tính Elo). Mọi cặp agent đủ đúng `games_per_pair` ván; không có `result` ngoài {-1,0,1}, không ván rỗng,
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

  **Đã chọn hướng 1 + 2** (chunk 11 đã chạy xong); kết quả ở mục 8. Các ô thời gian khác: 11x11@0,5 đạt (tệ nhất `mcts_ab_tac`
  0,19 %, 14/7.408 nước, max 2,56x); `failure_mining` @0,1 s cả 4 agent > 1 % (tệ nhất `mcts_random` 12,32 %), ô này chỉ để
  tìm ví dụ, không dùng để xếp hạng.

## 3. Nguồn dữ liệu của hình/bảng/failure_cases

* Hình lúc 09:36:09-18 và bảng 09:36:19, sau ván cuối (09:32:19), `summary.csv` (09:33:48) và `puzzles.csv`
  (09:36:07) của main_9x9. `experiments/plots.py` đọc `latest_runs` = thư mục `full` cho ablation_ab, ablation_mcts,
  scaling, main_7x7, main_9x9. Bảng `elo_ranking.tex` ghi 600 ván/agent (7x7) và 1.500 ván/agent (9x9, ô 1 s).
  Cột "games" của bảng là chỗ duy nhất ghi số ván; hình không ghi.
* **(Đã giải quyết)** `budget_modes` trước đây dùng dữ liệu quick (264 ván); sau chunk 9/10 đã sinh lại từ
  `results/nodes_budget/full` + `results/main_7x7/full` (mục 11).
* **(Đã giải quyết)** `failure_cases.md` bản cũ quét cả dữ liệu pilot/quick. Hiện chỉ quét thư mục `full`:
  **75.300 ván, đều FULL** (= 840 + 1.800 + 720 + 4.800 + 36.000 + 3.600 + 240 + 27.300; không tính bản lặp w6).
* Sửa nhỏ ngày 01/11 trong `experiments/plots.py`: `spearman` không xử lý hạng bằng nhau và thứ tự agent Elo bằng nhau phụ thuộc
  hash chuỗi, nên rho ở tiêu đề `budget_modes` đổi giữa các lần chạy (0,93 / 0,95). Đã dùng hạng trung bình + tie-break theo tên
  (có test); rho cố định = **0,94** (7x7: time@0,5 vs nodes@10000, 14 agent). Không đổi giao diện.
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

## 5. Failure cases (`results/failure_cases.md`, 75.300 ván FULL)

**Bản chốt: đủ 3 MCTS-miss + 3 AB-fail, đều từ dữ liệu FULL.** MCTS-miss: `mcts_random` x2 và `mcts_ab_tac` x1, cả ba từ
`main_11x11` (bỏ lỡ nước thắng win_in_3 đã được AB_FULL xác nhận). AB-fail: cả ba có `ab_plain` (depth 4 không ordering; ván
`9x5|t0.5`, `9x5|t0.1`, `7x4|n10000`), phù hợp phát hiện dưới đây rằng không có ca nào của AB có ordering. Phần còn lại của mục là phân tích trước chunk 7-10.

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

1. Ô 9x9@0.1 vi phạm budget (mục 2, 8); Elo ở ô này chỉ mang tính tham khảo. (Bản chốt đầy đủ ở mục 12.)
2. (Đã giải quyết) `budget_modes` đã sinh từ dữ liệu FULL.
3. Mọi AB đều giới hạn depth 4 (trừ `ab_full_timed`) và hết giờ phần lớn nước ở 9x9 (mục 4.2); kết luận về ID/TT/radius là về
   sức mạnh trong khung này.
4. So sánh nhiều cặp không hiệu chỉnh (Bonferroni); các "kết luận được" sát biên (CI chạm 0,5) nên đọc là gợi ý.
5. CI Elo neo Random bảo thủ; xem quy ước ở đầu file.

## 8. Đối chứng ô 9x9@0,1 s: 10 worker vs 6 worker

Cùng config, cùng seed và cùng 12.000 `game_id` (cùng thế khai cuộc); chỉ khác `--workers` (10 vs 6). Nguồn: `results/main_9x9/full/summary.csv`
(ô 0,1 s) và `results/main_9x9/full_w6_0.1/summary.csv`; violation tính lại từ `wall_s` từng nước.

* **Kendall tau Elo (16 agent) = 0,933**; bỏ Random 0,924; tau theo điểm số 0,933. Tức 4/120 cặp agent đảo thứ tự, đều là các cặp sát nhau (4 biến thể AB có order, MCTS lân cận).
* **Không agent nào có CI Elo tách biệt** (0/16). Chênh Elo (w6 - w10): AB có order -52...-65; MCTS +42...+70 (riêng `mcts_eval_tac` -16, `mcts_eval` -29);
  `backtracking_d2` +2; `ab_plain` +40. Trung bình |dElo| = 48, khoảng 1/3 nửa bề rộng CI (~±130). Ở mức cặp: 1/120 cặp có CI Wilson điểm số tách biệt (ngẫu nhiên kỳ vọng ≈ 6 ở mức 5 %).
* **Vi phạm budget (> 1,5x)**: tổng 3,05 % (10 worker) → 2,09 % (6 worker); số agent ≥ 1 %: 13 → 8.

| agent | Elo w10 [CI] | Elo w6 [CI] | vi phạm % w10 | vi phạm % w6 |
|---|---|---|---|---|
| ab_order_id_tt | 2659 [2539, 2801] | 2594 [2456, 2791] | 1,17 | 0,16 |
| ab_full | 2651 [2538, 2784] | 2597 [2463, 2780] | 1,57 | 0,02 |
| ab_order | 2650 [2537, 2788] | 2592 [2451, 2791] | 2,11 | 0,00 |
| ab_full_timed | 2648 [2533, 2775] | 2596 [2448, 2782] | 1,16 | 0,02 |
| mcts_eval_tac | 1638 [1524, 1773] | 1622 [1507, 1777] | 2,93 | 1,20 |
| mcts_eval | 1527 [1416, 1670] | 1498 [1386, 1652] | 2,36 | 0,29 |
| mcts_rave_tac | 1376 [1255, 1512] | 1439 [1325, 1593] | 6,35 | 5,90 |
| mcts_heuristic_tac | 1255 [1137, 1401] | 1324 [1208, 1478] | 6,43 | 6,20 |
| mcts_rave | 1190 [1085, 1317] | 1236 [1118, 1389] | 5,38 | 5,00 |
| mcts_ab_tac | 1071 [968, 1205] | 1113 [997, 1274] | 6,79 | 5,26 |
| backtracking_d2 | 1002 [893, 1141] | 1005 [887, 1162] | 0,02 | 0,00 |
| mcts_heuristic | 999 [886, 1142] | 1058 [932, 1217] | 4,80 | 5,09 |
| mcts_random | 952 [838, 1078] | 998 [881, 1152] | 1,81 | 1,09 |
| mcts_ab | 877 [782, 1024] | 946 [835, 1099] | 5,96 | 2,98 |
| ab_plain | 321 [246, 420] | 361 [282, 498] | 0,08 | 0,06 |
| random | 0 [0, 0] | 0 [0, 0] | 0,00 | 0,00 |

**Kết luận.** (1) Giả thuyết "lập lịch 10 worker" **đúng một phần**: với AB, vi phạm gần như biến mất khi giảm tải (1,2-2,1 % → ≤ 0,16 %) và Elo của AB giảm ~55 (ít được "tặng" thêm thời gian);
với các MCTS dùng rollout nặng (rave, heuristic, TAC, `mcts_ab*`) vi phạm **vẫn 5-6 %**, nên phần lớn là do độ thô của việc kiểm tra đồng hồ trong MCTS chứ không phải tải máy.
(2) **Dữ liệu 10 worker dùng được, không cần thay bằng 6 worker**: thứ hạng và mọi kết luận ở mục 4 và 10 không đổi (tau 0,93, 0 agent tách CI), và giữ 10 worker làm bản chính giúp ô 0,1 s cùng chế độ tải với ô 0,5 s và 1 s.
Bản 6 worker giữ làm bản lặp độc lập (cùng kết luận). (3) Không được khẳng định tuân thủ budget ở 0,1 s với bất kỳ bản nào (8-13 agent vẫn ≥ 1 %); báo cáo ghi nhãn budget-noisy kèm hai con số trên.
Khoảng cách AB-MCTS ở 0,1 s: +1.021 [+991, +1.051] (10 worker) và +975 [+881, +1.051] (6 worker).

## 9. So sánh bổ sung

### 9.1 11x11 (k=5, 0,5 s, 100 ván/cặp, 9 agent; Random = 0)

Nguồn: `results/main_11x11/full/summary.csv`. Roster rút gọn (9/16 agent), nên Elo 11x11 **không so tuyệt đối** với 7x7/9x9.

| agent | Elo [95 % CI] (score) |
|---|---|
| ab_order_id_tt | 2225 [2078, 2641] (0,95) |
| ab_full | 2157 [2015, 2570] (0,92) |
| mcts_eval_tac | 1545 [1403, 1928] (0,69) |
| mcts_eval | 1464 [1333, 1840] (0,65) |
| mcts_heuristic_tac | 1175 [1049, 1551] (0,49) |
| mcts_ab_tac | 914 [803, 1297] (0,33) |
| mcts_random | 830 [709, 1199] (0,28) |
| backtracking_d2 | 686 [562, 1065] (0,20) |
| random | 0 [0, 0] (0,00) |

### 9.2 Khoảng cách AB tốt nhất - MCTS tốt nhất (@0,5 s trừ khi ghi khác)

Khoảng cách Elo lấy từ **cùng một mẫu bootstrap** (300 lần lấy lại ván, seed 1), nên CI của hiệu hẹp hơn việc đặt hai CI Elo cạnh nhau (vốn chồng lấn vì dùng chung neo Random).
Agent tốt nhất chọn theo ước lượng điểm.

| bàn @ budget | AB tốt nhất | MCTS tốt nhất | khoảng cách Elo [CI] | đối đầu trực tiếp (điểm AB [Wilson]) |
|---|---|---|---|---|
| 7x7 k=4 @0,5 | ab_order 1742 | mcts_eval_tac 1646 | **+97 [+50, +139]** | 0,65 [0,50, 0,78] (n=40; chứa 0,5) |
| 9x9 k=5 @0,5 | ab_order 2376 | mcts_eval_tac 1908 | **+468 [+414, +516]** | 0,94 [0,88, 0,97] (n=100) |
| 11x11 k=5 @0,5 | ab_order_id_tt 2225 | mcts_eval_tac 1545 | **+680 [+595, +832]** | 0,97 [0,92, 0,99] (n=100) |
| 9x9 @0,1 (10 w) | ab_order_id_tt 2659 | mcts_eval_tac 1638 | +1.021 [+991, +1.051] | 1,00 [0,96, 1,00] |
| 9x9 @0,1 (6 w) | ab_full 2597 | mcts_eval_tac 1622 | +975 [+881, +1.051] | 1,00 [0,96, 1,00] |
| 9x9 @1,0 | ab_order 2182 | mcts_eval_tac 1850 | +332 [+297, +370] | 0,92 [0,85, 0,96] |

Khoảng cách tăng theo kích thước bàn: 7x7 → 9x9 và 9x9 → 11x11 đều **CI tách biệt** (so khác bàn/roster chỉ mang tính định hướng: Elo mỗi bàn neo riêng và roster 11x11 nhỏ hơn).
Khoảng cách giảm theo budget ở 9x9 (+468 → +332 giữa 0,5 s và 1,0 s: CI tách; 0,1 s bị nhiễu budget).

### 9.3 Time-budget vs nodes-budget (Kendall tau trên Elo, các agent chung; bootstrap 100 lần cho cả hai phía)

`mcts_ab`, `mcts_ab_tac` không có trong nodes_budget nên so 14 agent. Nguồn: `main_7x7/full`, `main_9x9/full` (0,5 s) với `nodes_budget/full`.

| cặp so sánh | ván (time / nodes) | tau [CI 95 %] | tau bỏ Random |
|---|---|---|---|
| 7x4 (7x7 k=4): 0,5 s vs 2000 | 4.800 / 9.100 | 0,835 [0,76, 0,91] | 0,808 |
| 7x4: 0,5 s vs 10000 | 4.800 / 9.100 | 0,813 [0,67, 0,90] | 0,782 |
| 9x5 (9x9 k=5): 0,5 s vs 2000 | 12.000 / 9.100 | 0,879 [0,82, 0,93] | 0,859 |

Cấu trúc giống hệt ở cả 3 cặp: {4 AB có order} > {MCTS} > `backtracking_d2` > `ab_plain` > Random; mọi bất đồng thứ hạng nằm **trong** nhóm AB (4 biến thể cách nhau < 40 Elo) hoặc trong nhóm MCTS.
Mốc nhiễu để đọc tau: hai lần chạy cùng budget (10 vs 6 worker) cũng chỉ đạt 0,93. Khác biệt đáng chú ý: ở nodes@10000 (7x4) khoảng cách AB-MCTS giữ ~100-110 Elo (time: 97) và các MCTS TAC/rave/heuristic gần như ngang nhau (1.805-1.819);
ở 9x5 `backtracking_d2` thấp hơn nhiều ở node budget (611 so với 1.041 ở time budget) — chưa tìm nguyên nhân, ghi nhận như khác biệt giữa hai chế độ đo. **Kết luận: nhất quán** về thứ tự nhóm; kết luận không phụ thuộc vào nhiễu tải/CPU của phép đo thời gian.

## 10. Findings cuối cùng

Quy ước mức chắc chắn: **tách biệt** = CI (Elo của hiệu, hoặc Wilson của đối đầu) loại trừ 0 / 0,5; **chồng lấn** = không loại trừ.

1. **Alpha-beta có sắp xếp nước đi thắng MCTS tốt nhất ở mọi bàn, và khoảng cách tăng theo kích thước bàn.** Hiệu Elo AB - MCTS: +97 [+50, +139] (7x7), +468 [+414, +516] (9x9), +680 [+595, +832] (11x11, roster rút gọn);
   đối đầu 0,65 [0,50, 0,78] / 0,94 [0,88, 0,97] / 0,97 [0,92, 0,99]. Mức chắc chắn: 9x9 và 11x11 **tách biệt**; ở 7x7 hiệu Elo tách khỏi 0 nhưng đối đầu trực tiếp (40 ván) **chồng lấn** (chứa 0,5).
   Nguồn: `main_7x7`, `main_9x9`, `main_11x11` `/full/summary.csv`; mục 9.2.
2. **Move ordering là thành phần duy nhất của alpha-beta có tác dụng đo được lên sức mạnh.** `ab_order` vs `ab_plain` = 1,00 [0,96, 1,00] ở cả 3 budget 9x9 (1,00 [0,91, 1,00] ở ablation); số nút depth 4 giảm 63 lần (1.064.799 → 16.900).
   Iterative deepening, bảng chuyển vị, radius 2 + killer, depth 10 vs 4: **chồng lấn** (mọi CI chứa 0,5; ví dụ ID+TT vs ab_order 0,51 / 0,47 / 0,46). Nguồn: `ablation_ab/full`, `main_9x9/full`; mục 4.2.
3. **Lợi thế của AB thu hẹp khi budget tăng (9x9).** Hiệu Elo +468 [+414, +516] (0,5 s) → +332 [+297, +370] (1,0 s): **tách biệt**. Điểm ab_order vs mcts_eval_tac 0,94 → 0,92: **chồng lấn** (chỉ 0,1 s [0,96, 1,00] tách khỏi 1,0 s [0,85, 0,96]).
   Ô 0,1 s bị nhiễu budget nên không dùng làm điểm xu hướng độc lập. Nguồn: `main_9x9/full/summary.csv`; mục 4.1, 8, 9.2.
4. **Các kết luận không phụ thuộc vào cách đo budget.** Thứ hạng theo thời gian và theo node nhất quán (Kendall tau 0,81-0,88, CI trong [0,67, 0,93], so với mốc nhiễu 0,93 giữa hai lần chạy cùng cấu hình);
   cấu trúc nhóm AB > MCTS > backtracking > ab_plain > Random giống hệt; bất đồng chỉ nằm trong từng nhóm (CI Elo **chồng lấn** ở đó). Nguồn: `nodes_budget/full`, `main_7x7/full`, `main_9x9/full`; mục 9.3, hình `budget_modes`.
5. **TAC giúp MCTS ổn định, còn RAVE phụ thuộc bàn.** TAC: `mcts_heuristic_tac` vs `mcts_heuristic` 0,85 [0,71, 0,93] (ablation) và 0,88 / 0,86 / 0,82 (9x9, 100 ván/ô); đều **tách biệt**; mọi MCTS TAC giải 30/30 puzzle, không-TAC 0,83-0,87.
   RAVE: 0,72 ở 9x9 (tách) nhưng 0,325 [0,20, 0,48] ở 7x7 (**tách**, chiều ngược) nên là đặc trưng bàn. CI Elo của cả 10 biến thể ablation **chồng lấn**, nên các kết luận này dựa trên đối đầu trực tiếp. Nguồn: `ablation_mcts/full`, `main_7x7/full`, `main_9x9/full`; mục 4.3.

## 11. Figure và bảng sẽ dùng trong báo cáo

Tất cả được sinh lại ngày 01/11 từ thư mục `full` (`experiments.plots`, `experiments.tables`, log `results/logs/postprocess.log`); không còn figure/bảng nào dùng quick/pilot.
Đã kiểm: sinh lại từ bản sao chỉ chứa `.jsonl.gz` cho **bảng .tex và PNG trùng byte (sha256)** với bản trong `results/`.

| đường dẫn | nội dung | dữ liệu / số ván |
|---|---|---|
| `results/figures/elo_vs_budget.{png,pdf}` | Elo từng agent theo budget, 3 panel 7x7 / 9x9 / 11x11 | main_7x7 4.800 + main_9x9 36.000 + main_11x11 3.600 = 44.400 ván |
| `results/figures/h2h_heatmap.{png,pdf}` | ma trận điểm đối đầu 7x7 | main_7x7: 4.800 ván |
| `results/figures/scaling_winrate.{png,pdf}` | AB vs MCTS theo kích thước bàn (7x4, 9x5, 11x5) | scaling: 720 ván (240/bàn) |
| `results/figures/ablation_ab.{png,pdf}` | ablation alpha-beta 9x5@0,5 s | ablation_ab: 840 ván |
| `results/figures/ablation_mcts.{png,pdf}` | ablation MCTS 9x5@0,5 s | ablation_mcts: 1.800 ván |
| `results/figures/nodes_vs_depth.{png,pdf}` | số nút theo depth, các cấu hình AB | `ablation_ab/full/nodes_vs_depth.csv` (đếm tất định, không phải ván) |
| `results/figures/puzzle_accuracy.{png,pdf}` | độ chính xác 30 puzzle x 16 agent | `main_9x9/full/puzzles.csv` (không phải ván) |
| `results/figures/budget_modes.{png,pdf}` | thứ hạng time@0,5 s vs nodes@10000 (7x7 k=4), Spearman rho 0,94 | main_7x7 4.800 + nodes_budget 7x4@10000 9.100 ván |
| `results/figures/nps_hist_9x9_0.5.{png,pdf}` | histogram nodes/s, 3 nước đầu, 3 agent | main_9x9 @0,5 s (12.000 ván). **Không có script sinh trong repo** (vẽ ad hoc 29/10 từ dữ liệu FULL); nếu dùng cần ghi rõ hoặc bổ sung script |
| `results/tables/elo_ranking.tex` | Elo + CI: 7x7@0,5 (600 ván/agent), 9x9@1,0 (1.500/agent), 11x11@0,5 (800/agent) | main_* summary |
| `results/tables/ab_ablation.tex` | ablation AB | ablation_ab: 840 ván |
| `results/tables/mcts_ablation.tex` | ablation MCTS | ablation_mcts: 1.800 ván |
| `results/tables/puzzle_accuracy.tex` | puzzle 30 thế | main_9x9 puzzles.csv |
| `results/tables/solve.tex` | kích thước cây / giá trị bài toán nhỏ (backtracking) | `results/solve.csv` (19/10; không phải thực nghiệm đối kháng) |
| `results/failure_cases.md` | 3 MCTS-miss + 3 AB-fail có bàn cờ | quét 75.300 ván FULL |

Không có figure riêng cho đối chứng 10 vs 6 worker và cho tau time-vs-nodes (chỉ có bảng ở mục 8, 9.3).

## 12. Limitations (bản chốt)

1. **Ô 9x9@0,1 s là budget-noisy.** 13/16 agent (10 worker) và 8/16 agent (6 worker) vượt 1 % số nước > 1,5x budget; vượt là tuyệt đối (~+50-60 ms ở đuôi). Đối chứng (mục 8): thứ hạng không đổi
   (tau 0,93, 0/16 agent tách CI) nhưng vi phạm của AB gần hết khi giảm tải còn của MCTS (5-6 %) thì không, nên nguyên nhân gồm cả lập lịch lẫn độ thô đồng hồ MCTS.
   Không dùng ô này để khẳng định tuân thủ budget. Các ô 0,5 s, 1 s, 11x11@0,5 đạt (< 1 %).
2. **Sự cố vận hành (dữ liệu không bị ảnh hưởng; đã kiểm toàn vẹn).**
   * *Pool treo ở chunk 9* (nodes_budget 7x4): START 29/10 14:37:06, không có dòng END; log chunk 9 chứa loạt `KeyboardInterrupt` của các `SpawnPoolWorker` (dừng tay), và chú thích trong `scripts/run_remaining.ps1`
     ghi pool treo ≈ 3,3 h mà không ai biết. **Thời điểm treo chính xác không được ghi lại** (games.jsonl không có timestamp từng ván). Khi resume 31/10 17:48 còn thiếu 10/18.200 ván (18.190 đã có), chạy bù 10 ván.
   * *Watchdog* (`StallMinutes = 20`, tự kill khi games file không lớn) được thêm sau sự cố này; **không kích hoạt lần nào** (không có dòng `WATCHDOG` trong `progress.txt`).
   * *Chunk 11* (bản lặp 6 worker): lần khởi động nhầm 31/10 16:30:39 (do `-DryRun` hỏng, đã ghi trong `progress.txt`) bị dừng tay ~16:40 sau **2.821 ván**; resume 16:59:45 chạy nốt 9.179 ván, xong 17:47:58. Tổng 12.000 ván, không trùng id.
   * *Chunk 10* (nodes_budget 9x5@2000): lần 1 kết thúc bất thường 19:11:27 (exit 1073807364) sau ~81 phút; lần 2 và bước post-processing chết ngay (exit -1073741205), tức tiến trình bị ngắt chứ không phải lỗi dữ liệu;
     chạy lại 01/11 00:08-01:43, chạy nốt 3.547 ván còn thiếu (5.553 ván đã có). Đây là sự cố ngoài danh sách ban đầu; nguyên nhân gốc chưa xác định.
3. **Toàn vẹn** (mục 1): không có `game_id` trùng trong từng run, cùng config với `experiments/configs/*.yaml`; riêng `main_9x9/full` và `full_w6_0.1` trùng 12.000 id có chủ đích (bản lặp), không bao giờ gộp.
4. **CPU lai** (Intel Core Ultra, 22 luồng, P/E-core), không ghim affinity: thông lượng trong cùng một thế thay đổi tới ~2-3x (mục 6); nhiễu này nằm trong CI đã báo. Chỉ có dữ liệu từ một máy.
5. **`--workers 10` cố định** cho mọi run chính (chunk 11 dùng 6 làm đối chứng); không quét theo số worker nên ảnh hưởng của số worker chỉ được định lượng bằng đối chứng 10 vs 6 ở ô 0,1 s (mục 8).
6. **Roster khác nhau giữa các ô**: 11x11 chỉ 9/16 agent; nodes_budget 14/16 (không `mcts_ab`, `mcts_ab_tac`); 9x5@10000 nodes bỏ (`skip_cells`). Elo neo Random theo từng ô nên không so tuyệt đối giữa bàn/budget/roster.
7. So sánh nhiều cặp không hiệu chỉnh Bonferroni; các kết luận sát biên (CI chạm 0,5, ví dụ 7x7) đọc là gợi ý. Mọi AB giới hạn depth 4 (trừ `ab_full_timed`) và hết giờ phần lớn nước ở 9x9 (mục 4.2).
8. Failure cases: AB-fail chỉ gặp với `ab_plain` (không có ca nào của AB có ordering trong 75.300 ván); cả 3 ví dụ MCTS-miss đến từ 11x11.

## 13. Nén dữ liệu và đóng gói

* Nén (`scripts/compress_jsonl.py`, ngưỡng 20 MB, gzip tất định): `main_9x9/full` 123,9 → 22,9 MB; `main_9x9/full_w6_0.1` 47,7 → 8,6 MB; `nodes_budget/full` 65,9 → 11,2 MB.
  Ba file `.gz` giải nén **trùng byte** với `games.jsonl` (sha256). File `.jsonl` gốc bị `.gitignore` (chỉ `.gz` được commit và đóng gói). Vì `.gitignore` loại mọi `games.jsonl` trong `full*`, các file < 20 MB (ablation_ab, ablation_mcts, scaling, main_7x7, main_11x11, failure_mining) cũng được nén (`--min-mb 0`) để dữ liệu chốt nằm trong git; cả 9 `.gz` trùng byte với bản gốc.
* **Checksum `summary.csv`**: dựng lại từ chính các `.gz` (`summarise` của `experiments.run`, bootstrap seed 0) cho ba run trên, **trùng byte** với `summary.csv` đã lưu
  (sha256 `4658167258108f14…`, `3f755f4df2a3ecac…`, `ae0e0fbed06d28a7…`).
  Sinh lại bảng và figure từ bản sao `results/` chỉ có `.gz`: 5/5 bảng `.tex` và 8/8 PNG trùng byte.
* `scripts/make_submission.py` (tên thử `FINALCHECK`): 187 file, **zip 52,5 MB** (nội dung 88,2 MB); giải nén vào thư mục tạm, venv sạch, `pip install -r requirements.txt`,
  `pytest -m "not slow"`: 222 passed, "verification: OK". Zip thử nằm ngoài repo; tên nhóm thật cần truyền lại bằng `--name`.
* Toàn bộ test (kể cả slow): 256 passed; `mypy --strict core agents`: không lỗi.

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
