# REPORT_OUTLINE — dàn ý báo cáo HW2 (CO3061, Topic 1)

Trạng thái: **bản dàn ý chờ nhóm duyệt**. Chưa viết `REPORT.md`. Không sửa code, không chạy lại thực nghiệm; các số trong
dàn ý này hoặc lấy từ `results/FULL_RUN_SUMMARY.md` hoặc được tính lại bằng script chỉ-đọc (ghi rõ ở Phần A).
Hạn nộp theo `HW2.pdf`: **CN 8/11/2026 23:59** (trễ −10 %/ngày, tối đa 3 ngày); `HW2.pdf` yêu cầu: zip, mã nguồn + PDF,
họ tên đầy đủ và đóng góp 0–100 % của từng thành viên, một bài nộp/nhóm; 5 tiêu chí: Problem Formulation, Originality,
Level of Challenge, Documentation, On-Time. Topic 1 liệt kê: Backtracking, Alpha-beta, MCTS, so sánh các phương pháp,
kèm GUI mô phỏng và tài liệu thuật toán chi tiết.

Quy ước nguồn trong dàn ý: `FRS` = `results/FULL_RUN_SUMMARY.md` (kèm số mục); `S` = `summary.csv` của run `full` tương ứng.

---

## Phần A. Các điểm cần nhóm quyết định hoặc xác nhận trước khi viết

Đây là những chỗ yêu cầu của bạn khác với dữ liệu trong repo, hoặc thiếu nguồn. Tôi đề xuất cách xử lý ở cột phải; cần bạn gật đầu.

| # | Vấn đề | Dữ liệu thực tế | Đề xuất |
|---|---|---|---|
| A1 | "7×7 k=4 người đi trước thắng ~65 %" | Điểm của X (bên đặt quân đầu tiên) trên `main_7x7`: **0,641 [0,627; 0,654]**, 3075 thắng / 1725 thua / 0 hoà, 4.800 ván; trên `scaling`: 0,662 [0,601; 0,719], 720 ván. 9×9: 0,521 [0,513; 0,530] (12.000 ván, ba budget gộp); 11×11: 0,511 [0,495; 0,528] (3.600 ván). Nguồn: `eval.stats.first_move_win_rate` (chỉ-đọc). Lưu ý: opening gồm 2–4 quân ngẫu nhiên ở trung tâm (`make_opening`), nên "X" là bên đặt quân đầu chứ không nhất thiết là bên đi trước sau opening. | Viết "≈ 64 % [63; 65]" (không viết 65 %), nói rõ định nghĩa, và nêu rằng thiết kế đổi bên/opening cân bằng triệt tiêu phần lớn thiên lệch nhưng bàn nhỏ vẫn lệch. Con số này cần được lưu lại: tôi sẽ để script `check_report.py` tính lại từ `games.jsonl.gz`. |
| A2 | Lý do chọn (N,k) | Repo chưa ghi lý do (AUDIT mục 5 câu 2). Chỉ có dữ kiện: k=4 ở 7×7, k=5 ở 9×9 và 11×11; 3×3, 4×3, 4×4 giải chính xác (solve.csv). | Viết 1.4 bằng lập luận nhóm nêu được từ dữ liệu: k=5 là luật Gomoku quen thuộc; k=4 ở 7×7 giữ ván không bị hoà gần như chắc chắn nhưng ván ngắn (trung bình 8,7 nước/ván, `runtime_estimate.md`) và khả năng phân biệt agent thấp. **Phần "vì sao nhóm chọn đúng k này" cần nhóm xác nhận** `[TODO: nhóm xác nhận lý do chọn k]`; tôi không bịa động cơ. |
| A3 | `results/OMITTED_DATA.md` | **Không tồn tại trong repo**: nó chỉ được sinh bên trong zip `--lite` (`scripts/make_submission.py`). sha256 các file bị lược đã có trong zip thử, tôi tính lại được bằng `sha256sum` trên 4 file `.gz` lớn. | Phụ lục B lấy sha256 từ chính các file `.gz` (script chỉ-đọc), link Drive/Release để `[TODO: link dữ liệu đầy đủ]`. Nếu muốn có `OMITTED_DATA.md` trong repo, đó là việc ngoài phiên này. |
| A4 | "16 lõi vật lý / 22 luồng" | `environment.txt` chỉ ghi `logical_cpus: 22` và CPU "Intel64 Family 6 Model 170" (Core Ultra theo FRS). Số lõi vật lý không có trong file nào. | Ghi 22 luồng logic (có nguồn); "16 lõi vật lý" kèm `[TODO: nhóm xác nhận số lõi vật lý]`. |
| A5 | Kết quả sửa clock check "Elo 1528 → 950 / 1128" | Nguồn là pilot, **chỉ 10 ván/cặp** (`PROGRESS.md` dòng ~178) nên CI rất rộng. Violation 67,7 → 0,00 % và 70,2 → 0,09 % có trong FRS 4.5 (pilot → pilot2 → full). | Dẫn cả hai và ghi rõ cỡ mẫu 10 ván/cặp cho phần Elo; chỉ dùng phần Elo như minh hoạ ảnh hưởng của việc vượt budget, không như phép so sánh có CI. |
| A5b | Kendall tau vs Spearman | Hình `budget_modes` hiển thị Spearman ρ = 0,94 (7×7: time@0,5 vs nodes@10000, 14 agent); Kendall tau 0,835 / 0,813 / 0,879 nằm trong bảng FRS 9.3, **không có hình**. | Dùng bảng cho tau, hình cho ρ; giải thích hai thước đo và nhắc rằng ρ đã được sửa tie-handling (mục 3.6). |
| A6 | Hình bùng nổ node (4.3) | `results/figures/` chưa có hình log-scale "node theo độ sâu so với công thức đóng" cho backtracking (`nodes_vs_depth` là hình của AB ablation). Có sẵn bảng `backtracking_growth.csv` (7×7 k=4, depth 1–5). | Mặc định chỉ dùng bảng. Nếu muốn hình, cần một script vẽ nhỏ (ngoài phạm vi "chỉ viết báo cáo"); hỏi bạn có cho phép không. |
| A7 | Ảnh GUI | `results/gui_screenshots/` có 3 ảnh sinh headless (`demo_setup`, `demo_numbers`, `demo_mcts_overlay`), không phải chụp tay. | Chèn 3 ảnh này kèm nhãn "ảnh sinh bằng `--headless-check`/screenshot của app", còn mục "ảnh chụp tay + link video" để `[TODO: nhóm bổ sung]`. |
| A8 | Bố cục số liệu theo quy tắc 1 (mỗi con số có nguồn) | Một số con số là **đại lượng tính từ công thức** (độ phức tạp, chương 2.2) chứ không đo. | Gắn nhãn `<!-- source: formula, kiểm bằng scripts/check_report.py -->`, đối chiếu với `bound_nodes` trong `backtracking_growth.csv` và 549.946 trong `solve.csv`. |
| A9 | Bootstrap theo ván, ID/TT, trọng số tay, radius 2 | Có trong yêu cầu và FRS; sẽ viết thẳng trong Limitations và 4.12. | Không cần quyết định. |

---

## Phần B. Dàn ý theo đề mục (đến cấp 3)

Mỗi mục: **nguồn số liệu** → nội dung chính. Số trang là ước lượng thô khi sang PDF (tổng mục tiêu 40–48 trang).

### Trang bìa, bảng đóng góp, mục lục (~2 trang)
* Bìa theo yêu cầu: ĐHQG-HCM / ĐH Bách Khoa / Khoa KH&KT Máy tính; CO3061; tên đề tài; GVHD: Nguyễn Quốc Minh; thành viên + MSSV `[TODO]`; "TP. Hồ Chí Minh, 11/2026".
* Bảng đóng góp: STT | Họ tên | MSSV | Tỷ lệ `[TODO]`, ghi chú đồng thuận `[TODO]`. Đầu `REPORT.md` có mục "Việc nhóm cần hoàn thiện" liệt kê mọi `[TODO]`.

### INTRODUCTION (~3 trang)
* **Giới thiệu và cách nhóm hiểu đề** — nguồn: `HW2.pdf`, `CLAUDE.md` (Goal). Mục tiêu là so sánh có kiểm soát ba phương pháp, không phải xây agent mạnh nhất.
* **Bảng "Đối chiếu với yêu cầu của đề"** — cột: Yêu cầu | Cách thực hiện | Mục. Hàng: Backtracking (2.3, 3.4, 4.2–4.3); Alpha-beta (2.4, 4.4); MCTS (2.5, 4.5); so sánh (4.6–4.8); GUI mô phỏng (3.8); tài liệu thuật toán chi tiết (Chương 2–3); bàn 7×7/9×9/11×11 (4.6); họ tên + % đóng góp (bảng đầu); đúng hạn 8/11/2026.
* **Những điểm khác với cách hiểu thông thường** — nguồn: `CLAUDE.md`, configs. k theo N (4/5/5); luật freestyle (overline thắng; `exact_k` tắt được); so sánh theo cả time budget và nodes budget; thêm hybrid và tactical check; bàn nhỏ giải chính xác để có "sự thật nền".
* **3–5 findings** — nguồn: FRS mục 10; mỗi finding một câu kèm số + CI (xem Phần C để chọn đúng con số).

### Chương 1 – Tổng quan và bối cảnh (~4 trang)
* **1.1 Bối cảnh** — m,n,k-game, Gomoku; 3×3 hoà; Gomoku tự do 15×15 người đi trước thắng (Allis 1994, `[TODO: kiểm tra trích dẫn]`). Không số liệu của nhóm.
* **1.2 Vấn đề nghiên cứu** — nguồn: FRS mục 10. Câu hỏi RQ1: AB (có ordering) so với MCTS thế nào khi bàn lớn dần? RQ2: thành phần nào của AB/MCTS thực sự đóng góp? RQ3: kết luận có phụ thuộc cách đo budget (time vs nodes)? RQ4: tốc độ cài đặt Python ảnh hưởng gì?
* **1.3 Mục tiêu** — tổng quát và cụ thể (đúng cấu trúc HW1).
* **1.4 Phạm vi** — cấu hình (N,k) ∈ {(3,3),(4,3),(4,4),(5,4) giải; (7,4),(9,5),(11,5) thi đấu}; 16 agent (11×11: 9 agent); budget 0,1/0,5/1,0 s và 2000/10000 node; phần cứng một máy. Nguồn: `experiments/configs/*.yaml`, `environment.txt`. Chứa lập luận chọn (N,k) (xem A1, A2).
* **1.5 Giới hạn nghiên cứu** — tóm tắt, chi tiết ở 5.2.

### Chương 2 – Cơ sở lý thuyết và phát biểu hình thức (~9 trang)
* **2.1 Formulation** — nguồn: `core/board.py`, `core/rules.py`, `CLAUDE.md`. $S$, $s_0$, ACTIONS, RESULT, TERMINAL-TEST, UTILITY ∈ {+1,0,−1}; freestyle vs exact-k; nước đi là số nguyên phẳng $r\cdot N+c$.
* **2.2 Độ phức tạp** — nguồn: công thức + `results/solve.csv` + `backtracking_growth.csv`. Bảng theo (N,k): $|S|\le 3^{N^2}$, branching ban đầu $N^2$, độ sâu tối đa $N^2$, số node cây đầy đủ $\sum_{d=0}^{D}\prod_{i=0}^{d-1}(N^2-i)$ (cận trên, chưa cắt ở trạng thái kết thúc); đối chiếu 549.946 (3×3, **tính cả node gốc**, nhỏ hơn cận trên vì ván kết thúc sớm) và `bound_nodes` của 7×7 (depth 1–4 khớp đúng 50 / 2.402 / 112.946 / 5.197.970).
* **2.3 Minimax / Backtracking** — nguồn: `agents/backtracking.py`, `docs/specs/P2_backtracking.md`. Phương trình minimax/negamax, memo, symmetry, early stop.
* **2.4 Alpha-beta và cải tiến** — nguồn: `agents/alphabeta.py`, `agents/evaluation.py`, `docs/specs/P3_alphabeta.md`, `P6_eval.md`. Cắt tỉa $\alpha$–$\beta$ (Knuth & Moore), move ordering, iterative deepening, transposition table + Zobrist, candidate moves (radius), killer; hàm đánh giá theo pattern. Nêu tính chất: cắt tỉa giữ nguyên giá trị minimax **ở cùng độ sâu và không radius**; preset thi đấu (radius 2) không được đảm bảo (test value-equality so `AB_PLAIN` với `AB_FULL` khi radius=None).
* **2.5 MCTS** — nguồn: `agents/mcts.py`, `P4_mcts.md`. Bốn pha; UCB1/UCT $\bar X_i+c\sqrt{\ln N/n_i}$; rollout random và heuristic; RAVE với $\beta=\sqrt{k/(3N+k)}$ (hoặc dạng đúng trong code, **kiểm lại khi viết**); tree reuse; tactical root check (TAC): thắng ngay / chặn ngay / win-in-3.
* **2.6 Hybrid** — nguồn: `agents/hybrid.py`, `P5_hybrid.md`. `MCTS_EVAL` (lá = đánh giá tĩnh), `MCTS_AB` (lá = AB depth 2, giá trị nén $(1-\tanh(s/\text{scale}))/2$, kẹp ±0,999). Nêu rõ: kỹ thuật đã biết (Baier & Winands `[TODO: kiểm tra trích dẫn]`).

### Chương 3 – Thiết kế và cài đặt (~9 trang)
* **3.1 Kiến trúc** — nguồn: `CLAUDE.md` (Architecture + 10 quyết định thiết kế). Sơ đồ Mermaid core → agents → eval → experiments/gui; liệt kê quyết định (move là int, Agent ABC, `SearchStats`, `copy(track_candidates)`, make/unmake, board bất biến sau `select_move`).
* **3.2 Board engine** — nguồn: `core/board.py`, `results/bench_core.csv` hoặc `bench_*` (**kiểm tên file khi viết**), `PROGRESS.md`. Win check incremental $O(k)$, Zobrist, candidate tracking tăng dần; số đo hiệu năng lấy từ file bench.
* **3.3 Hàm đánh giá** — nguồn: `agents/evaluation.py`. Công thức pattern và **bảng trọng số** (nêu rõ đặt tay, không sensitivity analysis).
* **3.4 Mã giả từng agent** — code block cho Backtracking, AB (+ID+TT), MCTS, RAVE, TAC, Hybrid; độ phức tạp thời gian/bộ nhớ.
* **3.5 Hạ tầng thực nghiệm** — nguồn: `eval/tournament.py`, `elo.py`, `stats.py`, `puzzles.py`, `scripts/run_remaining.ps1`. Round-robin, đổi lượt X/O, opening 2–4 quân trung tâm tất định theo seed, Bradley–Terry + prior 0,1 ván hoà ảo, neo Random=0, bootstrap 200 lần resample theo ván (hơi lạc quan), Wilson CI, 30 puzzle (3 loại), resume theo `game_id`, watchdog 20 phút.
* **3.6 Lỗi đã phát hiện và sửa** — mỗi lỗi: triệu chứng / nguyên nhân / cách test bắt. (i) tree reuse MCTS; (ii) clock check của hybrid (violation 67,7→0,00 % và 70,2→0,09 %, FRS 4.5; Elo pilot 10 ván/cặp, xem A5); (iii) cột `violations` cộng cả hai phía (`random` báo 9/79 vi phạm; test `test_violations_are_attributed_to_the_slow_agent`); (iv) Spearman không xử lý hạng bằng nhau + thứ tự phụ thuộc hash (rho 0,93↔0,95 → 0,94; test `test_spearman_ties_use_average_ranks`); (v) `failure_cases.py` quét cả dữ liệu pilot và chặn 400 ván đầu. Nguồn: `PROGRESS.md`, FRS 3, 4.5.
* **3.7 Kiểm thử** — nguồn: thư mục `tests/` (số file test sẽ đếm lại khi viết), kết quả 259 passed ở lần chạy đầy đủ gần nhất (gồm test chậm). Nguyên tắc tham chiếu độc lập (brute force, 549.946, vị trí kiểm tay); các gate: board bất biến, mypy `--strict` trên `core/` `agents/`, headless GUI, resume không trùng ván.
* **3.8 GUI** — nguồn: `gui/app.py`, `gui/controller.py`, `P8_gui.md`, `results/gui_screenshots/`. Tính năng, heatmap MCTS, PV line, hướng dẫn; ảnh sinh tự động + `[TODO: ảnh chụp tay, link video]`.

### Chương 4 – Thực nghiệm và đánh giá (~16 trang)
* **4.1 Thiết lập** — nguồn: `environment.txt`, `configs/*.yaml`, FRS đầu file + mục 1. Phần cứng (22 luồng; lõi vật lý theo A4), Python 3.10.11, numpy 1.26.4; budget, ván/cặp (40 ở 7×7 và ablation, 100 ở 9×9/11×11/nodes_budget), seed, `--workers 10`; **75.300 ván FULL** + 12.000 ván bản lặp 6 worker (không tính vào Elo chính). Bảng 75.300 = 840 + 1.800 + 720 + 4.800 + 36.000 + 3.600 + 240 + 27.300.
* **4.2 Giải chính xác bằng Backtracking** — nguồn: `results/solve.csv`, `tables/solve.tex`. Bảng (3,3) hoà (549.946 / 16.168 / 2.271 node theo none / memo / memo+symmetry), (4,3) người đi trước thắng, (4,4) hoà (chỉ memo+symmetry giải trong 120 s: 6.460.009 node, 60,99 s), (5,4) không giải trong 600 s. Diễn giải cơ chế: memo gộp transposition, symmetry chia ~8 lần.
* **4.3 Bùng nổ node trên 7×7** — nguồn: `results/backtracking_growth.csv`. Bảng depth 1–5: nodes đo = `bound_nodes` đến depth 4 (5.197.970 node, 15,0 s), depth 5 chạm trần 60 s. Hình: xem A6.
* **4.4 Ablation Alpha-beta** — nguồn: `ablation_ab/full` (840 ván, 9×5@0,5 s), `main_9x9/full` (100 ván/cặp × 3 budget), `nodes_vs_depth.csv`, hình `ablation_ab`, `nodes_vs_depth`. (a) số node: 1.064.799 → 16.900 (ordering, 63 lần) → 22.339 (+ID) → 18.959 (+TT) → 9.461 (radius 2 + killer) ở depth 4, n=3 thế (mô tả, không CI); (b) sức chơi: ordering 1,00 [0,96; 1,00] (n=100); ID, TT, radius, depth 10 **chưa phân biệt được** (mọi CI chứa 0,5). Giải thích cơ chế: AB hết giờ ở 52–86 % số nước trên 9×9 (`ab_plain` ~100 %) nên ID hiếm khi hoàn thành thêm một tầng; TT bị xoá mỗi `select_move`; nước dự phòng theo điểm cục bộ đã gần depth 2–3. **Không viết "ID vô tác dụng".**
* **4.5 Ablation MCTS** — nguồn: `ablation_mcts/full` (1.800 ván, 40 ván/cặp), `main_9x9/full`, `main_7x7/full`, hình `ablation_mcts`, bảng `mcts_ablation.tex`. c_uct (chưa phân biệt), rollout heuristic vs random (chưa phân biệt, riêng 0,1 s 0,63 tách), tree reuse (chưa phân biệt), TAC (0,85 [0,71; 0,93]), RAVE (9×9 0,72 tách; 7×7 0,325 [0,20; 0,48] tách chiều ngược). Giải thích cơ chế RAVE đảo chiều theo kích thước bàn (AMAF chia sẻ thống kê giữa các nhánh: hữu ích khi nhiều nước độc lập, có hại khi ván ngắn và thế mang tính chiến thuật cục bộ), nêu đó là giả thuyết, không được kiểm chứng riêng.
* **4.6 Tournament chính** — nguồn: `main_7x7/full`, `main_9x9/full`, `main_11x11/full` (`summary.csv`), hình `elo_vs_budget`, `h2h_heatmap` (7×7), bảng `elo_ranking.tex`. Bảng Elo + CI (FRS A2, A3, 9.1). Cấu trúc nhóm: AB có ordering > MCTS > `backtracking_d2` > `ab_plain` > Random. Hybrid `mcts_ab` kém `mcts_heuristic` ở 9×9 (0,29–0,30, CI tách) vì 150–170 mô phỏng/s. **Mọi bảng/hình dùng ô 9×9@0,1 s gắn nhãn "budget-noisy"** (8–13/16 agent vượt 1 %; đối chứng 6 worker: Kendall tau 0,933, 0/16 agent tách CI).
* **4.7 Ảnh hưởng kích thước bàn và first-move advantage** — nguồn: FRS 9.2, `scaling/full`, `first_move_win_rate`. Khoảng cách Elo best AB − best MCTS: **+97 [+50; +139] (7×7, n=4.800 ván; đối đầu 0,65 [0,50; 0,78], 40 ván, chưa phân biệt được)**, +468 [+414; +516] (9×9@0,5), +680 [+595; +832] (11×11, roster 9 agent). Bootstrap cặp cùng mẫu; so khác bàn chỉ mang tính định hướng (Elo neo riêng mỗi bàn). Lợi thế đi trước: 0,641 / 0,521 / 0,511 (A1). Cơ chế: bàn lớn → branching lớn, AB có ordering vẫn tận dụng được đánh giá cục bộ, còn rollout ngẫu nhiên MCTS loãng; nhưng đây là hệ quả của tốc độ Python (4.8).
* **4.8 Time budget vs nodes budget** — nguồn: `nodes_budget/full` (27.300 ván), FRS 9.3, hình `budget_modes`. Kendall tau 0,835 [0,76; 0,91] (7×7: 0,5 s vs 2000), 0,813 [0,67; 0,90] (vs 10000), 0,879 [0,82; 0,93] (9×9: 0,5 s vs 2000), so với mức nhiễu nền 0,933 (hai lần chạy cùng cấu hình 10 vs 6 worker). Cấu trúc nhóm giống hệt, bất đồng nằm trong nhóm AB hoặc MCTS. Kết luận hẹp: **thứ hạng nhóm giữ nguyên khi bỏ yếu tố tốc độ thực thi**, nhưng AB > MCTS chỉ áp dụng cho cài đặt Python này (MCTS ~2–4k mô phỏng/s). `mcts_ab*` không có trong nodes_budget (14 agent). `backtracking_d2` ở 9×5 lệch (611 vs 1.041), chưa tìm nguyên nhân.
* **4.9 Tactical puzzles** — nguồn: `main_9x9/full/puzzles.csv`, `experiments/puzzles.json` (30 thế), hình `puzzle_accuracy`, bảng `puzzle_accuracy.tex`. AB có ordering 1,00; `backtracking_d2` 0,667; `ab_plain` 0,10; MCTS không TAC 0,83–0,87; mọi MCTS có TAC 1,00. Cơ chế: giá trị trung bình rollout bão hoà nên không phân biệt nước chặn bắt buộc; TAC cưỡng chế. Cỡ mẫu 10 puzzle/loại nên CI rộng, nêu rõ.
* **4.10 Phân tích thất bại** — nguồn: `results/failure_cases.md` (75.300 ván FULL), FRS 5. 3 MCTS-miss (`mcts_random` ×2, `mcts_ab_tac` ×1, **cả ba trên 11×11**, bỏ lỡ win-in-3 được AB_FULL xác nhận) và 3 AB-fail (**cả ba có `ab_plain`**: không ordering nên depth 4 không hoàn tất). Bàn cờ ASCII, giải thích cơ chế; **phạm vi hẹp**: không có ca nào của AB có ordering trong 75.300 ván; không khái quát cho mọi cấu hình.
* **4.11 Thảo luận** — khi nào dùng gì: bàn nhỏ có thể giải chính xác (backtracking+memo+symmetry); bàn vừa/lớn với ngân sách ngắn: AB có ordering; MCTS cần TAC; hybrid trả giá bằng số mô phỏng. Mỗi khẳng định gắn số ở 4.4–4.9.
* **4.12 Mối đe doạ tới tính hợp lệ** — nội bộ: bootstrap theo ván (lạc quan), không hiệu chỉnh đa so sánh, trọng số đặt tay, vi phạm budget ở 0,1 s; bên ngoài: một máy, CPU lai (histogram nodes/s không hai đỉnh, nhưng `ab_order_id_tt` có vai chậm hơn 1,6–2 lần, không coi là bằng chứng lõi P/E), Python; cấu trúc: roster khác nhau giữa các ô; kết luận: ở 7×7 CI chạm 0,5.

### Chương 5 – Kết luận và hướng phát triển (~3 trang)
* **5.1 Kết luận** — 5 phát hiện từ FRS mục 10, mỗi cái kèm số + CI + mức chắc chắn (tách / chưa phân biệt).
* **5.2 Hạn chế** — toàn bộ FRS mục 12 (budget-noisy 0,1 s; sự cố vận hành; CPU lai; `--workers 10`; roster khác nhau; đa so sánh; AB depth 4 và hết giờ; failure cases hẹp) cộng: Python, trọng số tay, bootstrap theo ván, radius 2 không bảo đảm giá trị minimax.
* **5.3 Hướng phát triển** — MCTS-Solver, threat-space search, tuning trọng số + sensitivity, cài đặt hiệu năng cao (C++/numba) để kiểm tra giả thuyết tốc độ, bản đồ độ nhạy $c_{uct}$/RAVE theo bàn.

### Phụ lục (~5 trang)
* **A. Cài đặt và chạy** — nguồn: `README.md`. GUI (`python -m gui.app`), test, mypy, chạy experiments, tái tạo bảng/hình (`plots`, `tables`, `failure_cases`, `nps_hist`).
* **B. Gói nộp** — nguồn: `scripts/make_submission.py`, README mục 7. Full: 52,5 MB; lite: 5,4 MB (181 file); 4 file `.gz` bị lược và sha256 (tính từ file, xem A3); link `[TODO]`.
* **C. Config và số ván** — nguồn: `configs/*.yaml`, FRS mục 1. Bảng run → ô → ván thực/dự kiến.
* **D. Nhật ký sự cố và toàn vẹn** — nguồn: FRS mục 12, `results/logs/progress.txt`. Chunk 9 treo ≈3,3 h (thời điểm không ghi lại); chunk 10 dừng 19:11:27 31/10, bù 3.547 ván (5.553 + 3.547 = 9.100, 9.100 game_id khác nhau, 91 cặp × 100); chunk 11 dừng sau 2.821 ván rồi resume 9.179 ván; không có `game_id` trùng trong từng run; hai run 9×9@0,1 s chia sẻ 12.000 id có chủ đích. Watchdog không kích hoạt.
* **E. FAQ / vấn đáp** — nguồn: `AUDIT_GRADER.md` mục 5 (10 câu) cập nhật số liệu FULL. Cần sửa: câu 6 và 7 (số cũ), câu 2 (lý do k, A2).

### Tài liệu tham khảo (IEEE, ~1,5 trang)
Russell & Norvig; Knuth & Moore 1975; Zobrist 1970; Kocsis & Szepesvári 2006; Browne et al. 2012; Gelly & Silver 2011; Allis 1994; Allis–van den Herik–Huntjens; Winands–Björnsson–Saito 2008; Baier & Winands. Tôi không có quyền truy cập thư viện trong phiên này, nên **mọi mục gắn `[TODO: kiểm tra trích dẫn]`** (tác giả/năm/venue theo trí nhớ, không DOI, không số trang).

---

## Phần C. Danh sách hình và bảng

### C1. Hình (đã có, tất cả sinh từ dữ liệu FULL; xem FRS mục 11)

| Hình | Đường dẫn | Dùng ở | Dữ liệu |
|---|---|---|---|
| Elo theo budget, 3 panel | `results/figures/elo_vs_budget.png` | 4.6 | main_7x7 + main_9x9 + main_11x11: 44.400 ván |
| Ma trận đối đầu 7×7 | `results/figures/h2h_heatmap.png` | 4.6 | main_7x7: 4.800 ván |
| Scaling AB vs MCTS | `results/figures/scaling_winrate.png` | 4.7 | scaling: 720 ván |
| Ablation AB | `results/figures/ablation_ab.png` | 4.4 | ablation_ab: 840 ván |
| Node theo depth (AB) | `results/figures/nodes_vs_depth.png` | 4.4 | `ablation_ab/full/nodes_vs_depth.csv` (đếm tất định) |
| Ablation MCTS | `results/figures/ablation_mcts.png` | 4.5 | ablation_mcts: 1.800 ván |
| Puzzle | `results/figures/puzzle_accuracy.png` | 4.9 | `main_9x9/full/puzzles.csv` (30 thế × 16 agent) |
| Time vs nodes | `results/figures/budget_modes.png` | 4.8 | main_7x7 4.800 + nodes_budget 7×4@10000 9.100 |
| Histogram nodes/s | `results/figures/nps_hist_9x9_0.5.png` | 4.12 | main_9x9 @0,5 s (12.000 ván), 3 nước đầu của 3 agent |
| GUI | `results/gui_screenshots/demo_{setup,numbers,mcts_overlay}.png` | 3.8 | ảnh sinh tự động |
| Sơ đồ kiến trúc | (Mermaid trong văn bản) | 3.1 | — |
| Bùng nổ node (tuỳ chọn) | **chưa có** | 4.3 | cần script, xem A6 |

### C2. Bảng

| Bảng | Nguồn | Dùng ở |
|---|---|---|
| Đối chiếu yêu cầu của đề | `HW2.pdf` + mục chương | Introduction |
| Độ phức tạp theo (N,k) | công thức + `solve.csv`, `backtracking_growth.csv` | 2.2 |
| Giải chính xác (3,3) (4,3) (4,4) (5,4) | `results/solve.csv` | 4.2 |
| Node theo depth, 7×7 | `results/backtracking_growth.csv` | 4.3 |
| Số ván mỗi run (75.300) | FRS mục 1, `summary.csv` | 4.1, Phụ lục C |
| Node AB theo thành phần (n=3 thế) | FRS 4.2, `nodes_vs_depth.csv` | 4.4 |
| Ablation AB (đối đầu + CI) | `ablation_ab/full`, `main_9x9/full`; `tables/ab_ablation.tex` | 4.4 |
| Ablation MCTS | `ablation_mcts/full`; `tables/mcts_ablation.tex` | 4.5 |
| Elo + CI: 7×7@0,5, 9×9 (3 budget), 11×11@0,5 | `main_*/full/summary.csv`; `tables/elo_ranking.tex` | 4.6 |
| Vi phạm budget theo agent và ô | FRS A1 (tính lại từ `games.jsonl.gz` bằng script chỉ-đọc) | 4.1, 4.6, Phụ lục D |
| Đối chứng 10 vs 6 worker (9×9@0,1 s) | `main_9x9/full/summary.csv`, `full_w6_0.1/summary.csv` | 4.6, Phụ lục D |
| Khoảng cách AB − MCTS theo bàn/budget | FRS 9.2 | 4.7 |
| First-move advantage | `eval.stats.first_move_win_rate` | 4.7 |
| Kendall tau time vs nodes | FRS 9.3, `nodes_budget/full` | 4.8 |
| Puzzle theo agent và loại | `tables/puzzle_accuracy.tex`, `puzzles.csv` | 4.9 |
| Failure cases (6 ví dụ) | `results/failure_cases.md` | 4.10 |
| Config và số ván | `configs/*.yaml` | Phụ lục C |
| Sự cố vận hành | `logs/progress.txt`, FRS 12 | Phụ lục D |

---

## Phần D. Kế hoạch sau khi được duyệt

1. Viết từng chương vào `REPORT.md` (Introduction + bìa/đóng góp, rồi Chương 1 … Phụ lục), **mỗi chương một commit** "report: chương N".
2. Mọi số liệu/bảng/hình kèm `<!-- source: ... -->`; mọi `[TODO]` tập trung ở đầu file (mục "Việc nhóm cần hoàn thiện").
3. `scripts/check_report.py` (chỉ-đọc): trích số trong khối có `source`, đối chiếu `summary.csv`/`solve.csv`/`backtracking_growth.csv`/`FULL_RUN_SUMMARY.md`; tính lại các số dẫn xuất (khoảng cách Elo, tau, first-move) từ `games.jsonl.gz`; kiểm đường dẫn hình; chạy đến khi không lệch.
4. Ước lượng số trang (mục tiêu 30–50 trang PDF; dàn ý ở trên ~42–48 trang kể cả hình) rồi commit "report: final draft".

Ngôn ngữ cấm (quy tắc 3): không dùng "chứng minh" (trừ chứng minh toán học), "novel", "đột phá", "vượt trội", "hoàn hảo", "tối ưu", "SOTA" khi không có số liệu; `check_report.py` sẽ quét các từ này.

**Cần bạn duyệt**: (1) A1–A8 ở trên (đặc biệt A1 đổi 65 % thành ≈ 64 %, A2, A6); (2) bố cục chương/ước lượng trang; (3) cho phép (hay không) một script vẽ hình bùng nổ node. Sau khi bạn trả lời, tôi bắt đầu viết.
