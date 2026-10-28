# AUDIT_GRADER — chấm thử HW2 (CO3061, Topic 1) từ góc nhìn giảng viên

Ngày kiểm tra: 27/10/2026. Hạn nộp: **CN 8/11/2026 23:59** (trễ: −10 %/ngày, tối đa 3 ngày — theo `HW2.pdf`).
Commit kiểm tra: `f60d084` (working tree sạch). Phiên này **không sửa code, không commit**; file này là thay đổi duy nhất.
Nguyên tắc: chỉ ghi điều đã tự chạy/đọc được. Điều chưa kiểm chứng được có ghi rõ cách kiểm chứng.

---

## 0. Tóm tắt điều hành

### 0.1 Điểm dự kiến theo tiêu chí (thang 10)

Đề (`HW2.pdf`, đã đọc bằng `pypdf`) chấm 5 tiêu chí: Problem Formulation, Originality, Level of Challenge,
Documentation, On-Time. Không có trọng số công bố; tôi giả định bằng nhau.

| Tiêu chí | Hiện tại | Sau P0 + P1 | Lý do chính (một dòng) |
|---|---|---|---|
| Problem Formulation | **6.0** | 8.5 | Luật/định nghĩa nằm trong code + `CLAUDE.md`, nhưng chưa có văn bản hình thức (state/action/transition/terminal/utility), không có trích dẫn nguồn cho (N,k), không có phân tích độ phức tạp bằng số ngoài bảng node-explosion |
| Originality | **6.0** | 7.5 | Hybrid MCTS + tactical root check + ablation là ý tưởng đã biết (chính `REPORT_FOR_TEAM.md` §6.7 thừa nhận); "finding" thật chưa có số liệu FULL đỡ lưng |
| Level of Challenge | **7.0** | 8.5 | 3 thuật toán + 2 hybrid + Elo/Wilson/openings đổi màu + GUI + solver là khối lượng lớn; nhưng mọi ablation hiện chỉ có dữ liệu `--quick` (4 ván/cặp) |
| Documentation | **1.5** | 8.0 | **Chưa có PDF báo cáo, chưa có README, chưa có % đóng góp** — đây là lỗ hổng lớn nhất; code/figure/bảng chỉ là nguyên liệu |
| On-Time | chưa xác định | — | Chưa nộp; rủi ro nằm ở việc PDF chưa bắt đầu và full run chưa chạy |

Điểm trung bình hiện tại (nếu nộp đúng trạng thái hôm nay): **~5.2/10**. Dự kiến sau P0 + P1: **~8.1/10**.
(Con số này là ước lượng của người chấm, không phải đo được.)

### 0.2 Năm việc quan trọng nhất cần làm ngay

1. **Bắt đầu báo cáo PDF ngay** (tên đầy đủ + % đóng góp, formulation, thuật toán, kết quả, GUI, hạn chế). Không có nó thì 3/5 tiêu chí gần như không chấm được.
2. **Sửa MCTS clock-check cho hybrid AB-leaf** (hiện kiểm tra mỗi 64 sim, `agents/mcts.py:219`) và sửa cách đếm `violations` trong `eval/tournament.py:222-236`, rồi chạy lại pilot nhỏ để chứng minh tỉ lệ vi phạm < 1 % **trước khi** chạy full. Hiện `mcts_ab` / `mcts_ab_tac` vi phạm 67.7 % / 70.2 % nước đi trên 9x9 (tôi tự tính lại, §1.3).
3. **Quyết định tập thực nghiệm tối thiểu và khởi động full run tối nay** (chunk 1–3 nhỏ trước, chunk 4 sau khi sửa clock). Hiện **0 config nào đã chạy FULL** (§1.2).
4. **Thêm 11x11 vào so sánh chính** (đề nêu rõ 7x7, 9x9, 11x11; hiện 11x11 chỉ nằm trong `scaling.yaml`, 40 ván/cặp, 1 budget). Chạy pilot 11x11 10 phút trước để ước lượng thời gian thật.
5. **Viết README + ghim version trong `requirements.txt` + chốt gói zip** (bỏ thư mục quick-run cũ, `__pycache__`), và **tự chơi GUI bằng tay** ở 7/9/11 (mới chỉ test headless).

---

## 1. Bước 1 — Trạng thái thực tế (đã chạy lệnh)

### 1.1 Test, mypy, GUI

| Hạng mục | Kết quả | Bằng chứng |
|---|---|---|
| `python -m pytest -q` | **223 passed, 0 failed, 0 skipped** trong 643.8 s (10 phút 43 giây); khớp con số 223 trong `REPORT_FOR_TEAM.md`. Test chậm nhất: `test_backtracking.py::test_known_values` 76 s | lệnh chạy ở thư mục gốc repo, Python 3.10.11 |
| `python -m mypy` (strict, `core/` + `agents/`) | **Success: no issues found in 12 source files** (1.8 s) | cấu hình `pyproject.toml`: `strict = true`, `files = ["core","agents"]` |
| GUI headless | `SDL_VIDEODRIVER=dummy python -m gui.app --headless-check` → in `gui ok` | import + khởi tạo không lỗi. `tests/test_gui_app.py` có `test_window_is_large_enough_for_11x11` |
| Chơi GUI thật bằng tay | **Chưa kiểm chứng được** (môi trường không có màn hình) | Cách kiểm chứng: `python -m gui.app`, chơi 7x7/9x9/11x11 đủ 4 mode, theo `REPORT_FOR_TEAM.md` §5.1 |

Lưu ý: mypy strict **không** bao phủ `eval/`, `gui/`, `experiments/`, `tests/` (theo `pyproject.toml`); điều này đã được ghi trong `REPORT_FOR_TEAM.md` nên không phải vi phạm `CLAUDE.md`.

### 1.2 Thư mục `results/` — config nào đã chạy FULL?

Số ván thực tế đếm bằng `wc -l games.jsonl`; số ván dự kiến lấy từ `--dry-run` (chỉ đối với main) hoặc từ bảng trong `PROGRESS.md` (**chưa kiểm chứng lại bằng `--dry-run`** cho các config còn lại).

| Config | Thư mục chạy | Ván thực tế | Ván dự kiến FULL | Trạng thái |
|---|---|---|---|---|
| main_tournament | `20261019-053006` | 264 | **72,000** (`--dry-run` in `72000 games`) | chỉ `--quick` |
| nodes_budget | `20261019-053442` | 264 | 26,400 theo `PROGRESS.md` (chưa tính lại sau khi bỏ `mcts_ab*`) | chỉ `--quick` |
| ablation_ab | `20261019-053101` | 84 | 840 | chỉ `--quick` |
| ablation_mcts | `20261019-053307` | 112 | 1,120 | chỉ `--quick` |
| scaling | `20261019-053433` | 24 | 720 | chỉ `--quick` |
| failure_mining | `20261019-053723` | 240 | 240 | đủ số ván, nhưng 7x7 @0.1 s, chỉ 1 cấu hình |
| pilot_main | `pilot/` | 2,400 | 2,400 | **đủ**, nhưng chỉ 10 ván/cặp, budget 0.5 s |

Kết luận: **chưa có dữ liệu FULL nào** cho báo cáo. Dữ liệu duy nhất đủ lớn để rút nhận xét là pilot (2,400 ván, CI Elo ≈ ±200).

Phát hiện phụ: `PROGRESS.md` ghi main_tournament "39,600 ván / ~15 h", còn `--dry-run` cho **72,000 ván**. Bảng đó đã cũ; ước lượng 8.4 h trong `results/runtime_estimate.md` mới là số được dùng. Nên sửa `PROGRESS.md` hoặc xóa bảng để khỏi mâu thuẫn.

Ngoài ra `results/figures/` (16 file = 8 hình PDF+PNG) và `results/tables/*.tex` (5 bảng) được tạo từ dữ liệu quick, không dùng được để trích vào báo cáo.

### 1.3 Các follow-up đã yêu cầu — ĐÃ LÀM / CHƯA LÀM

| Follow-up | Trạng thái | Bằng chứng |
|---|---|---|
| Tactical root check (TAC) cho MCTS | **ĐÃ LÀM** | commit `3cb0266`; `tests/test_mcts_tactical.py` (17 test); báo cáo: block 20/20 seed ở ≤ 500 sim |
| Solver: early_stop switch + schema `solve.csv` mới | **ĐÃ LÀM** | commit `bb76cbd`; `results/solve.csv` 15 dòng, cột `early_stop` |
| Runtime pilot + chunk resumable | **ĐÃ LÀM** | commit `c6bfa5c`; `results/pilot_main/pilot` 2,400 ván; `results/runtime_estimate.md` |
| **Adaptive clock check cho MCTS (violation < 1 %)** | **CHƯA LÀM** | `agents/mcts.py:219` vẫn là `sims & 63` (kiểm tra mỗi 64 sim); không có commit nào sau `c6bfa5c` đụng tới agents; `REPORT_FOR_TEAM.md` §0.2 tự ghi "did not change". Số đo lại từ `pilot_main/pilot/games.jsonl` (tôi tự tính, wall time từng nước, ngưỡng 1.5× budget 0.5 s): `mcts_ab` 12.3 % (7x7) / **67.7 %** (9x9); `mcts_ab_tac` 12.9 % / **70.2 %**; max 3.98 s. 14 agent còn lại: **0 %**, max 1.31× budget (`mcts_rave_tac` 0.654 s). Yêu cầu < 1 % **chưa đạt** cho 2 agent này |
| Cấu hình bàn mới: thêm 11×11 vào so sánh chính | **CHƯA LÀM** | `experiments/configs/main_tournament.yaml`: `boards: [[7, 4], [9, 5]]`; 11x11 chỉ có trong `scaling.yaml` |
| Cấu hình "7×7 rút gọn" | **CHƯA LÀM / không xác định được** | Không có config hay commit nào mang nghĩa này; tôi không biết "rút gọn" là bớt agent, bớt ván hay bớt budget. Xin chốt lại ý (đề xuất ở P0-5) |
| Giới hạn bộ nhớ | **LÀM MỘT PHẦN** | Chỉ có `tt_size = 2**20` entry cho transposition table của alpha-beta (`agents/alphabeta.py:55`, cắt ở :357). MCTS không có trần số node (grep không thấy `max_nodes`); chưa đo RSS của 10 worker. Rủi ro thấp ở budget ≤ 1 s (≈ vài nghìn sim), chưa kiểm chứng ở nodes_budget = 10,000 sim |
| `n_workers` | **LÀM MỘT PHẦN** | `--workers N` (`experiments/run.py:4`), bị chặn bởi `max_workers()` = lõi vật lý − 1 (`eval/tournament.py:311`). `psutil` không có trong `requirements.txt` nên nhánh dự phòng là `cpu_count()//2` — kết quả phụ thuộc máy |

**Lỗi báo cáo vi phạm (mới phát hiện):** cột `violations` trong `summary.csv` **không phân biệt agent**. `eval/tournament.py:222-236` cộng vi phạm của *cả hai bên* vào mỗi ván, rồi gán cho cả hai agent. Bằng chứng: trong `pilot_main/pilot/summary.csv`, dòng `random` (wall time tối đa 0.000 s) có `violations = 9` ở 7x7, và `ab_full` có 8, 45 (7x7, 9x9) trong khi tự tính lại ra 0. Con số "52 % / 54 %" trong `REPORT_FOR_TEAM.md` §0.2 vì vậy cũng không khớp với số tính theo agent (12–70 % tùy bàn). Nếu nộp nguyên trạng, giảng viên nhìn bảng sẽ thấy `random` vi phạm thời gian.

### 1.4 Cài đặt từ máy sạch

| Mục | Kết quả |
|---|---|
| `requirements.txt` | Có 6 gói (numpy, PyYAML, matplotlib, pygame, pytest, mypy) nhưng chỉ có cận dưới `>=`, **không ghim version**. `psutil` thiếu (được `import` động ở `eval/tournament.py:313`). Thiếu `types-PyYAML` (mypy cho `eval/`, `experiments/`). Chưa thử `pip install -r` trong venv mới — **chưa kiểm chứng được** |
| README | **Không có** (`ls README*` không thấy). Hướng dẫn chạy GUI/test/experiments chỉ rải trong `PROGRESS.md` và `REPORT_FOR_TEAM.md` §4 |
| Python | 3.10.11 khớp `CLAUDE.md`; `pyproject.toml` không khai báo `requires-python` hay `dependencies` |

---

## 2. Bước 2 — Chấm theo rubric

### 2.1 Problem Formulation — 6.0/10

**Bằng chứng hiện có**
- Luật chơi chính xác nằm ở `CLAUDE.md` (Game definition) và `core/board.py`, `core/rules.py`: bàn N×N, ô ∈ {0,1,−1}, X đi trước, thắng khi k liên tiếp (freestyle, `exact_k` tùy chọn), hòa khi đầy bàn.
- Quyết định kỹ thuật (nước đi = int phẳng, `make/unmake`, candidate radius…) được ghi rõ ở `CLAUDE.md`.
- Có độ phức tạp bằng số cho backtracking: `results/backtracking_growth.csv` — 7x7 k=4, độ sâu 1..4 = 50 / 2,402 / 112,946 / 5,197,970 node, khớp **chính xác** công thức đóng 1+Σ∏(N²−j) (có test).

**Điểm giảng viên sẽ trừ**
1. **Câu hỏi 1 (bắt buộc trả lời): State, action, transition, terminal test, utility có được định nghĩa hình thức không?** — Không có văn bản nào trình bày dạng (S, s₀, ACTIONS, RESULT, TERMINAL-TEST, UTILITY). Chỉ có suy ra được từ code. Với báo cáo PDF thì đây là phần "Problem Formulation" cốt lõi.
2. **Lựa chọn (N,k) có lý do/nguồn không?** — Không. Tìm trong repo chỉ thấy "Allis-style" ở `docs/specs/P5_hybrid.md` (mô tả threat-space search chưa được xây). Không có chỗ nào giải thích vì sao k=4 cho 7x7, k=5 cho 9x9 và 11x11, cũng không có trích dẫn. `REPORT_FOR_TEAM.md` §6.11 tự nhắc "verify the citation".
3. **Phân tích độ phức tạp bằng số**: có b^d từ thực nghiệm backtracking, nhưng không có bảng cận state-space (3^{N²}) / số ván tối đa / branching factor trung bình cho 3x3, 7x7, 9x9, 11x11. Chưa có chỗ nào so sánh với số đo (ví dụ 549,946 node cho 3x3 có trong `solve.csv` nhưng chưa đặt cạnh bound).
4. Lý do chọn k: nếu k=4 trên 7x7 thì trò chơi rất chiến thuật và X thắng 65.6 % ván pilot (§2.5) — cần nói thẳng, không giấu.

**Để đạt 10/10:** mục "Problem Formulation" trong PDF gồm (i) 5 thành phần hình thức, (ii) bảng (N,k) với lý do + trích dẫn đã tra, (iii) bảng độ phức tạp: |S| ≤ 3^{N²}, độ sâu tối đa N², b₀ = N², số node tính bằng công thức đóng, đối chiếu số đo, (iv) nêu rõ freestyle vs exact-k và (v) biên giới những gì đã giải được (3x3, 4x4 draw, (4,3) X thắng; (5,4) chưa giải trong 600 s).

### 2.2 Câu 2 — Đủ yêu cầu đề?

| Yêu cầu `HW2.pdf` | Có? | Bằng chứng / thiếu |
|---|---|---|
| 1. Backtracking | Có | `agents/backtracking.py` (minimax vét cạn, make/unmake), solver `experiments/run_solve.py`, `solve.csv`, `backtracking_growth.csv` |
| 2. Alpha-beta | Có | `agents/alphabeta.py` + `evaluation.py`, 5 preset, `ab_ablation.csv` (ordering giảm ~100× node, cùng giá trị) |
| 3. MCTS | Có | `agents/mcts.py` (UCT / heuristic rollout / RAVE / tree reuse / TAC), `hybrid.py` |
| 4. So sánh | **Có pipeline, chưa có dữ liệu FULL** | pilot 2,400 ván dùng được tạm; tất cả bảng/hình hiện từ quick |
| GUI mô phỏng | Có | `gui/app.py`, `gui/controller.py`, preset N ∈ (3,4,7,9,11); 30 test (20 controller + 10 app) |
| Chơi được 7×7, 9×9, 11×11? | **Có trong test headless; chưa kiểm chứng bằng tay** | `tests/test_gui_app.py` mặc định N=11; ảnh `results/gui_screenshots/demo_*.png` |
| Tài liệu thuật toán chi tiết (PDF) | **Không** | chưa bắt đầu (`REPORT_FOR_TEAM.md` §0.1) |
| Tên thành viên + % đóng góp | **Không** | |
| Zip nộp LMS | Chưa | |

Thiếu rõ nhất: PDF, % đóng góp, 11x11 trong so sánh chính, `MCTS_SOLVER`/threat-space search (spec P5 để tùy chọn — không bị trừ nếu báo cáo ghi rõ).

### 2.3 Câu 3 — Tính đúng đắn

**(a) 4 thế forced win-in-3 — tôi tự kiểm chứng bằng solver viết riêng**, chỉ dùng thư viện chuẩn, không import code repo (`scratchpad/indep.py`, chạy `python -I`). Bốn thế lấy từ `tests/positions.py`, chép tay lưới ký tự:

| Thế | Win-in-1? | Nước thắng trong 3 ply (solver của tôi) | Khớp `Pos.best`? |
|---|---|---|---|
| `win_in_3_open_three_7x7` (k=4, X ở (3,2),(3,3)) | không | (3,1), (3,4) | khớp |
| `win_in_3_column_7x7` (X ở (1,3),(2,3)) | không | **chỉ** (3,3) | khớp |
| `win_in_3_open_four_9x9` (k=5, X ở (4,3..5)) | không | (4,2), (4,6) | khớp |
| `win_in_3_column_9x9` (X ở (2..4,6)) | không | (1,6), (5,6) | khớp |

Đối chiếu bằng tay (3 thế đầu): mở rộng thành 3 liên tiếp với cả hai đầu trống thì đối thủ chỉ chặn được một đầu, X hoàn thành k ở đầu kia; các nước lệch (ví dụ (0,3) hoặc (4,3) ở thế cột 7x7, hoặc (4,1)/(4,7) ở 9x9) để lại đúng một ô hoàn thành nên bị chặn. Đối thủ O trong các thế này không có đe dọa nào.
→ Kỳ vọng trong `positions.py` **đúng**, và `tests/test_positions.py` cũng tự tính lại bằng tìm kiếm vét cạn (`wins_within`, chỉ dùng `make/unmake` của Board) — đây là tham chiếu độc lập đúng nghĩa cho các thế trên.

**(b) (3,3) = hòa với đúng 549,946 node** — Đạt. `results/solve.csv` dòng `3,3,none,0,0,549946,3.349,1`; `tests/test_backtracking.py:158` assert `r.value == 0 and r.nodes == 549946`. Con số 549,946 là số node của cây trò chơi 3x3 đã biết trong literature (không phụ thuộc code), nên đây là tham chiếu độc lập tốt. Lưu ý: số này gồm cả node gốc; nên nói rõ trong báo cáo.

**(c) Value-equality AB_PLAIN vs AB_FULL** (`tests/test_alphabeta.py:54`, `:63`) — Đạt có điều kiện:
- Phủ 10 thế cố định (độ sâu 4 trên 7x7, 3 trên 9x9) + 3 midgame 9x9.
- *Điểm yếu 1*: tập so sánh là `ALL_NO_RADIUS`, tức `AB_FULL` **với radius = None**, không phải preset `ab_full` thật đang thi đấu (radius 2). Giá trị của preset thi đấu chỉ được đối chiếu gián tiếp qua `ab_ablation.csv` (cùng nước đi trên 3 midgame).
- *Điểm yếu 2*: các preset dùng chung module `evaluation.py`, nên lỗi trong hàm đánh giá không bị phát hiện bởi test này. Chỗ độc lập duy nhất là `test_plain_value_matches_backtracking_on_4x4` (trọng số đánh giá = 0, so với BacktrackingAgent) — nên nêu rõ trong báo cáo.

**(d) Sign convention của MCTS — chỉ độc lập một phần.** `tests/test_mcts.py:71`: với từng preset, trên thế win-in-1 (7x7, 9x9) và bản `mirror` đổi màu (O đi), nước thắng phải có `Q == 1.0` và là Q lớn nhất (rollout ngẫu nhiên: tập argmax ⊆ `best`). Kỳ vọng lấy từ thế dựng tay → độc lập. Nhưng test chỉ chạm trường hợp *terminal-child*; lỗi dấu ở các tầng giữa cây (backprop xen kẽ) chỉ bị bắt gián tiếp qua test "block" (cần đúng dấu ở độ sâu 2) và `MCTS_AB` win-in-3. Đề nghị bổ sung một test win-in-3 cho MCTS thuần (Q của nước thắng > Q của nước lệch, cả hai màu) — việc ~1 giờ.

**Giới hạn chưa kiểm chứng:** (4,4) = hòa và (4,3) = X thắng là kết quả solver của nhóm; `REPORT_FOR_TEAM.md` §6.11 tự nói chưa đối chiếu literature. Đối chiếu độc lập: chạy brute-force không memo cho (4,3) với early_stop (79 s, đã có trong `solve.csv`) — nhưng đó vẫn là code của nhóm. Chưa có nguồn ngoài.

### 2.4 Câu 4 — Công bằng khi so sánh

| Hỏi | Trả lời | Bằng chứng |
|---|---|---|
| Equal time budget được tôn trọng? | **14/16 agent: có. `mcts_ab`, `mcts_ab_tac`: không** | Bảng §1.3. Mean wall time của hai agent này 1.07 s / 1.02 s ở budget 0.5 s (2.1× — `runtime_estimate.md` cột `fill` 2.15 / 2.04). Elo của chúng trong pilot (1380/1407 ở 7x7, 1528/1528 ở 9x9) vì vậy **được lợi** từ thời gian nghĩ nhiều hơn → so sánh time-budget với 2 agent này hiện không công bằng |
| Violation rate từng agent | Xem §1.3; cột `violations` trong `summary.csv` **sai** (cộng cả hai bên) | `eval/tournament.py:222-236` |
| Có đổi lượt đi trước? | **Có** | Game id dạng `…\|o2\|s0`: mỗi opening chơi với `s0`/`s1` (đổi màu); opening 2–4 quân gần tâm, giống nhau cho mọi cặp |
| Wilson CI hẹp hơn ±10 %? | **Chỉ khi ≥ ~100 ván/cặp** | Tôi tính Wilson 95 % tại p=0.5: n=10 → [0.237, 0.763] (±26 %); n=40 → ±14.8 %; n=100 → [0.404, 0.596] (±9.6 %); n=200 → ±6.9 %. Vậy pilot (10 ván/cặp) và 3 config ablation/scaling (40 ván/cặp) **không** đạt ±10 % ở mức từng cặp; chỉ main/nodes_budget (100) đạt, sát ngưỡng. CI trên điểm gộp theo agent (150–1,500 ván) hẹp hơn nhiều |
| Time-budget và nodes-budget nhất quán? | **Chưa kiểm chứng được** | nodes_budget chỉ có quick (264 ván); ở 7x7 @2000 node, 8 agent hòa đúng 0.636 vì X thắng mọi opening ngắn (`REPORT_FOR_TEAM.md` §6.4) — chưa có tín hiệu. Cách kiểm chứng: chạy chunk 9 (7x4@2000, ≈0.55 h) rồi so thứ hạng với 7x4@0.5 bằng Spearman/Kendall |

Các điểm công bằng khác cần ghi vào báo cáo: 10 tiến trình song song trên lõi siêu phân luồng → nhiễu thời gian; 14 agent đều chạy Python thuần nên kết luận "AB > MCTS" chỉ áp dụng cho cài đặt này (pilot: MCTS ≈ 2–4 k sim/s).

### 2.5 Câu 5 — Originality: finding thật hay chỉ thêm tính năng?

Số liệu pilot (10 ván/cặp, CI Elo ≈ ±200 — **tất cả đều sơ bộ**):

| Ứng viên finding | Số liệu | Đánh giá |
|---|---|---|
| (A) Thứ tự nước đi làm giảm ~100× node mà giá trị minimax giữ nguyên | `ab_ablation.csv`: AB_PLAIN 1.94 M node / 57.7 s vs AB_ORDER 16.3 k / 1.4 s (cùng value + move trên 3 midgame 9x9) | **Mạnh nhất, đã có dữ liệu cuối** (xác định, tái lập được). Nhưng "ordering giảm node" là kiến thức giáo khoa — giá trị nằm ở việc đo và kiểm chứng value-equality |
| (B) Khoảng cách AB − MCTS tăng theo cỡ bàn | Elo tốt nhất AB vs tốt nhất MCTS: 7x7 1528 vs 1472 (−56); 9x9 2106 vs 1819 (−287) | **Ứng viên hay nhất cho phần mở đầu**, nhưng CI chồng lấn lớn và chưa có 11x11 → chưa thể khẳng định. Cần dữ liệu FULL + 11x11 |
| (C) Heuristic rollout *không tốt hơn* random rollout nếu thiếu tactical check ("saturation") | 9x9 pilot: `mcts_heuristic` 1068 vs `mcts_random` 1126; puzzles win-in-1: heuristic 0.6 vs random 1.0 ở 0.3 s (từ `REPORT_FOR_TEAM.md`, chưa tự tái chạy) | Thú vị và phản trực giác; cơ chế giải thích có sức thuyết phục (nhiều nước cùng giá trị 1.0 nên visit count không chọn nước thắng). Hiệu số 58 Elo nằm trong nhiễu. Cần FULL |
| (D) TAC cứu heuristic MCTS | 9x9: +274 Elo (heuristic), +135 (eval), +95 (rave); 7x7: +49 / +48 / 0 | Đúng hướng và nhất quán giữa 3 biến thể, nhưng CI chồng; chỉ nên coi là "finding" nếu FULL xác nhận với CI không chạm nhau |
| (E) Tăng cỡ bàn: `ab_plain` chỉ ngang `random` khi có time limit | pilot: 300 / 482 Elo | Tác dụng phụ của thiết kế baseline, không phải finding |

Nhận định: phần "originality" hiện là *so sánh có kiểm soát + ablation*, đúng như `REPORT_FOR_TEAM.md` §6.7 đã thừa nhận. Không nên dùng chữ "novel". Đưa lên đầu báo cáo: (B) nếu FULL xác nhận, kèm (C)+(D) làm cơ chế giải thích; (A) làm "kiểm chứng đúng đắn".

### 2.6 Câu 6 — Level of Challenge: ablation có tách được từng kỹ thuật?

| Ablation | Tách được gì | Khoảng trống |
|---|---|---|
| AB: PLAIN → ORDER → ORDER_ID → ORDER_ID_TT → FULL (`ablation_ab.yaml`, `ab_ablation.csv`) | Đóng góp lần lượt của ordering, iterative deepening, TT, candidate radius — đến mức **node** (đo xong, quyết định) | Mức **sức chơi** mới có quick (84 ván). Phát hiện đáng chú ý: ID và TT *tăng* node ở độ sâu cố định (21.8 k, 19.2 k vs 16.3 k); lợi ích chỉ là anytime — nên nói rõ. Không có ablation riêng cho killer/history (nếu có trong code) |
| MCTS: c_uct, rollout, RAVE, TAC, reuse (`ablation_mcts.yaml`) | Từng yếu tố, một biến mỗi lần | Quick = 112 ván → vô nghĩa thống kê; không có tương tác TAC × rollout; không đổi hệ số RAVE |
| Hybrid: MCTS_EVAL, MCTS_AB | Loại lá (random / heuristic / eval tĩnh / AB sâu 2) | Overshoot thời gian làm hỏng so sánh (§1.3). `MCTS_SOLVER` chưa xây |
| Evaluation weights (hand-set, hình học) | **Không có** ablation hay sensitivity | `REPORT_FOR_TEAM.md` §6.6 tự nhận; giảng viên hay hỏi "trọng số lấy từ đâu" |
| Cỡ bàn / k | `scaling.yaml`: 3 bàn, 1 budget, 40 ván/cặp | Cần ít nhất 11x11 trong main hoặc scaling FULL ≥ 100 ván |

### 2.7 Câu 7 — Documentation readiness

| Sản phẩm cho báo cáo | Có dữ liệu đủ? | Ghi chú |
|---|---|---|
| Bảng node explosion (backtracking) | **Có, cuối cùng** | `backtracking_growth.csv` (xác định) |
| Bảng solver (3x3, 4x3, 4x4, 5x4) | **Có, cuối cùng** | `solve.csv`; (5,4) ghi "không giải được trong 600 s" |
| Bảng ablation AB về node | **Có, cuối cùng** | `ab_ablation.csv` |
| Bảng/hình MCTS throughput | Có | `bench_mcts.csv` (9x9 / 11x11 sims/s) |
| Bảng Elo xếp hạng chính | **Chỉ pilot** (10 ván/cặp) | `elo_ranking.tex` hiện từ quick |
| Elo vs budget, heatmap h2h, ablation MCTS, nodes-vs-time, scaling | **Chỉ quick** | 8 hình hiện tại là minh họa pipeline |
| Puzzle accuracy | Quick (30 puzzle @0.1 s) | Cần chạy lại ở 0.5 s, `--extras` |
| Failure cases | 3 MCTS-miss + **1** AB-fail; cần 3 AB-fail | `results/failure_cases.md` ← cần full run |
| Bảng LaTeX | Chưa biên dịch lần nào | cần `booktabs` |
| GUI screenshots | 3 ảnh headless | cần ảnh từ chơi thật |
| Trích dẫn tài liệu | **Không có** | xem danh sách gợi ý ở P1-6 |

---

## 3. Bước 3 — Kế hoạch cải thiện

Mốc: hôm nay 27/10 → hạn nộp 8/11, **hạn nội bộ 6/11** (buffer 2 ngày) = 10 ngày làm việc. Giờ máy ước lượng từ
`results/runtime_estimate.md` (mô hình hiệu chỉnh từ pilot; sai số trong mẫu ±10 %, ngoài mẫu **chưa kiểm chứng**).

### P0 — bắt buộc trước khi nộp

| # | Vấn đề | Tác động | Công sức (người + máy) | Rủi ro | Hành động cụ thể |
|---|---|---|---|---|---|
| P0-1 | Chưa có PDF báo cáo, % đóng góp | Cao | 20–30 h người + 0 | Cao nếu để cuối | Dàn ý ở `REPORT_FOR_TEAM.md` §6.1; viết formulation + thuật toán **song song** với full run; điền tên/% sớm để cả nhóm xác nhận |
| P0-2 | Overshoot thời gian của `mcts_ab*` + cột `violations` sai | Cao (công bằng so sánh) | 2 h người + 0.3 h máy | Thấp | `agents/mcts.py:219`: chu kỳ kiểm tra clock thành thuộc tính lớp (64 cho `MCTSAgent`, 1 cho hybrid AB-leaf); `eval/tournament.py:222-236`: đếm vi phạm theo agent (lưu `violations_x/violations_o` hoặc tính từ `moves`); thêm 1 test; rồi `python -m experiments.run --config experiments/configs/pilot_main.yaml --run-dir results/pilot_main/pilot2` và kiểm tra bằng script tương tự §1.3 → mục tiêu < 1 % mỗi agent. Cần người chấp thuận vì `CLAUDE.md` cấm đổi interface |
| P0-3 | Không có dữ liệu FULL | Cao | 3 h người + ~26 h máy (lịch §4) | Trung bình (máy ngủ, nhiễu tải) | Chạy chunk 1–9 của `REPORT_FOR_TEAM.md` §4 theo thứ tự đã cắt giảm (§4 dưới); sau đó `python -m experiments.plots / tables / failure_cases` |
| P0-4 | 11x11 chưa có trong so sánh chính | Cao (đề nêu rõ) | 2 h người + ≈ 8 h máy (ngoại suy) | Trung bình — ước lượng 11x11 là ngoại suy từ 9x9 | Chạy pilot 11x5@0.5 s (10 ván/cặp, ~15–30 min) để đo độ dài ván/tốc độ thật; thêm `[11, 5]` vào `boards` của bản config **rút gọn** (xem §4, ≤ 10 agent) |
| P0-5 | Chưa rõ "7×7 rút gọn" | Trung bình | 0.5 h người | Thấp | Chốt nghĩa với nhóm; đề xuất: bộ agent rút gọn 10–11 agent cho 7x7/9x9/11x11 (bỏ biến thể trùng lặp) |
| P0-6 | Không có README, `requirements.txt` không ghim | Cao (Documentation) | 2 h người | Thấp | Tạo `README.md`: cài đặt (`python -m venv`, `pip install -r requirements.txt`), `python -m gui.app`, `python -m pytest -q`, `python -m mypy`, lệnh chạy experiments + thời gian; ghim bằng `pip freeze`; thêm `psutil` hoặc bỏ nhánh `importlib`; thêm `requires-python = ">=3.10"` |
| P0-7 | GUI chưa được người chơi thử; gói zip chưa tạo | Cao | 3 h người | Thấp | Làm `REPORT_FOR_TEAM.md` §5.1 ở 7/9/11; chụp ảnh thật; chỉ zip `core agents eval gui experiments tests docs results/{figures,tables,pilot_main,full runs} README.md requirements.txt`, xóa quick-run cũ và `__pycache__`; **thử giải nén và `pip install` + `pytest` trong venv sạch** |

### P1 — tăng điểm rõ rệt, làm được trong 10 ngày

| # | Vấn đề | Tác động | Công sức | Rủi ro | Hành động |
|---|---|---|---|---|---|
| P1-1 | Formulation hình thức + bảng độ phức tạp bằng số | Cao | 3 h người | Thấp | Viết (S, s₀, ACTIONS, RESULT, TERMINAL-TEST, UTILITY ∈ {+1,0,−1}); bảng: N, k, \|S\|≤3^{N²}, b₀=N², độ sâu tối đa, node cây đầy đủ theo công thức đóng, nhánh trung bình đo từ pilot |
| P1-2 | Cluster/paired bootstrap theo opening | Trung bình | 1 h người | Thấp | `eval/stats.py`: resample theo opening (hiện resample ván nên CI lạc quan, `REPORT_FOR_TEAM.md` §6.8). Chỉ sửa sau khi nhóm đồng ý (ngoài phạm vi phiên này) |
| P1-3 | Test sign MCTS ở tầng sâu | Trung bình | 1 h | Thấp | Thêm test win-in-3 cho MCTS thuần trên thế đã tự kiểm chứng ở §2.3(a), cả hai màu |
| P1-4 | Sensitivity của trọng số đánh giá | Trung bình | 2 h người + ~1 h máy | Thấp | `ablation_ab`-style: nhân trọng số threat ×0.5/×2, bỏ số hạng threat; 9x5@0.5, 100 ván/cặp |
| P1-5 | Kiểm chứng time vs nodes | Trung bình–Cao | 1 h + 0.55 h máy | Thấp | chunk 9 phần `7x4@2000`; Kendall tau giữa hai bảng xếp hạng; ghi vào báo cáo |
| P1-6 | Tài liệu tham khảo | Trung bình | 1.5 h | Thấp (nhưng **phải tra thật**) | Tra và kiểm tra từng mục trước khi in: Allis (1994) *Searching for Solutions in Games and Artificial Intelligence*; Allis, van den Herik, Huntjens, Go-Moku solved (1996); Knuth & Moore 1975; Kocsis & Szepesvári 2006 (UCT); Gelly & Silver 2011 (RAVE); Winands, Björnsson, Saito 2008 (MCTS-Solver); Baier & Winands (MCTS-minimax hybrids); Browne et al. 2012 (survey). Tôi nhớ các tên này nhưng **chưa tra lại năm/venue** — cần kiểm chứng |
| P1-7 | Failure cases cần 3 AB-fail | Trung bình | 0.5 h | Thấp | Sau khi chạy main FULL: `python -m experiments.failure_cases`; nếu < 3 thì tăng `failure_mining.yaml` (240 ván chỉ cần vài phút) |
| P1-8 | Nhãn thống kê trên hình/bảng | Thấp–Trung bình | 1 h | Thấp | Mọi hình ghi n ván/cặp + CI; bỏ kết luận ở cặp CI chồng lấn |

### P2 — nên có nếu dư thời gian

| # | Vấn đề | Tác động | Công sức | Hành động |
|---|---|---|---|---|
| P2-1 | MCTS-Solver (proven win/loss) | Trung bình | 6–8 h người | `Node.proven` đã có; spec P5 để tùy chọn |
| P2-2 | Chạy lại 1 cell trên máy thứ hai | Thấp–Trung bình | 1 h + máy | Kiểm tra tái lập (§2.4) |
| P2-3 | Thêm 1 ván demo GUI (GIF/video) | Thấp | 1 h | Dùng cho phần thuyết trình |
| P2-4 | Giới hạn bộ nhớ MCTS (trần node) | Thấp | 1 h | chỉ nếu đo RSS thấy bất thường |
| P2-5 | mypy cho `eval/` (+ `types-PyYAML`) | Thấp | 1.5 h | mở rộng `files` trong `pyproject.toml` |

## 4. Lịch chạy full theo chunk ≤ 6 h và phương án cắt giảm

Ước lượng (giờ máy, `runtime_estimate.md`): ablation_ab 0.24, ablation_mcts 0.31, scaling 0.11, main 8.35, failure_mining ≈ 0, nodes_budget 16.64 → **25.7 h**, cộng 11x11 ≈ +8.1 h (ngoại suy).
Ước lượng trên giả định **chưa** sửa overshoot; sau sửa, `mcts_ab*` nghĩ ngắn lại nên tổng giảm nhẹ.

| Ngày | Việc | Máy |
|---|---|---|
| 27–28/10 | P0-2 (sửa + pilot lại), chunk 1–3 (0.6 h), pilot 11x11 | ~2 h |
| 28–29/10 (qua đêm) | chunk 4: main 7x4 mọi budget + 9x5@0.1/0.5 (5.0 h) | 5 h |
| 29–30/10 | chunk 5: 9x5@1 + puzzles (3.3 h); chunk 6 failure_mining | 3.4 h |
| 30–31/10 (qua đêm) | 11x11 main: `--only 11x5@0.1 11x5@0.5 11x5@1`, chia `--part` nếu mỗi chunk > 6 h | ~8 h |
| 1–2/11 | chunk 9 phần `7x4@2000 7x4@10000 9x5@2000` (5.5 h) | 5.5 h |
| 2–4/11 | nếu còn thời gian: chunk 7–8 (`9x5@10000`, 11.2 h) | 11.2 h |
| 4–6/11 | plots / tables / failure_cases, biên dịch LaTeX, đóng gói, thử giải nén | — |

**Phương án cắt giảm** (khi chậm), theo thứ tự bỏ trước:
1. **Bỏ `nodes_budget` 9x5@10000** (11.2 h). Lý do: chỉ là kiểm tra độ bền; `9x5@2000` + `7x4@*` đã đủ để so sánh thứ hạng với time-budget.
2. **Bỏ budget 1.0 s ở 9x5** (3.3 h) và giữ 0.1 / 0.5. Mất điểm Elo-vs-budget thứ ba; vẫn còn 2 điểm + 7x4 đủ 3 điểm.
3. **Rút gọn agent ở 11x11** còn ≈ 8 (`random, backtracking_d2, ab_order_id_tt, ab_full, mcts_random, mcts_eval, mcts_eval_tac, mcts_heuristic_tac`) và 1 budget (0.5 s): ≈ 1–2 h thay vì 8 h. Đây là phiên bản "rút gọn" tối thiểu đáp ứng đề.
4. **Không cắt**: ablation_ab, ablation_mcts, scaling (chỉ 0.7 h, chứa phần "challenge"), main 7x4 & 9x5@0.5 (lõi so sánh), failure_mining (phút).

Giữ ≥ 100 ván/cặp cho các cặp quan trọng (tại p = 0.5, Wilson n=100 mới đạt ±9.6 %). Với các baseline yếu (random, ab_plain, backtracking_d2) kết quả lệch (p gần 0 hoặc 1) nên 20–30 ván là đủ; nhưng `games_per_pair` hiện là một hằng số cho toàn config → cần tách config (thay đổi ngoài phạm vi phiên này). Mọi chunk resumable (chạy lại cùng lệnh); đề nghị tắt sleep/hibernate, cắm điện, không chạy việc nặng khác — kết quả time-budget nhạy với tải.

---

## 5. Bước 4 — 10 câu vấn đáp

1. **Vì sao MCTS cần tactical root check?**
   Vì rollout/giá trị trung bình không phân biệt nước thắng ngay khi nhiều nước cùng giá trị ≈ 1.0 (saturation): heuristic MCTS không chặn được đe dọa ở 1,500 sim trên 7x7 (~40 %), cần 3,000 sim (7x7) hoặc 8,000 (9x9) mới 10/10; với TAC thì 20/20 seed ở ≤ 500 sim. Dẫn chứng: `tests/test_mcts.py` (`block_rate`), `tests/test_mcts_tactical.py`, `PROGRESS.md` mục P4/TAC. (Con số 40 %/10-10 lấy từ tài liệu nhóm, tôi chưa tự chạy lại.)
2. **Vì sao chọn k=5 cho 9x9 và k=4 cho 7x7?**
   Hiện **không có lý do ghi lại trong repo**. Trả lời được duy nhất nếu nhóm bổ sung: k=5 là luật gomoku freestyle quen thuộc (Allis 1994 — cần tra), k=4 giữ trò chơi không bị hòa tầm thường trên 7x7. Số liệu bất lợi cần thừa nhận: 7x7 k=4, X thắng 65.6 % ván pilot, ván dài 8.5 ply. Dẫn chứng: `pilot_main/pilot/summary.csv`.
3. **Alpha-beta có làm thay đổi kết quả minimax không?**
   Không — cắt tỉa an toàn giữ nguyên giá trị gốc; sau cải tiến (ordering, ID, TT) cũng giữ nguyên ở cùng độ sâu vì TT chỉ dùng ở cùng depth còn lại và bị xóa mỗi lần gọi. Chứng cứ: `tests/test_alphabeta.py::test_pruning_and_enhancements_do_not_change_the_minimax_value` (10 thế), `…_9x9_midgames` (3 thế), `…_matches_backtracking_on_4x4`; `ab_ablation.csv` cùng value/move. Lưu ý ngoại lệ: candidate radius 2 không được đảm bảo (§2.3c).
4. **Vì sao backtracking không giải được 5x4 hay 7x7?**
   Số node tăng như tích N²(N²−1)…: 7x7 depth 4 = 5.2 M node (15 s), depth 5 ước 234 M. Chứng cứ: `backtracking_growth.csv` khớp công thức đóng, `solve.csv` (5,4) chưa giải trong 600 s dù có memo + đối xứng.
5. **549,946 là gì và vì sao tin được?**
   Số node của cây trò chơi tic-tac-toe 3x3 đầy đủ (kể cả gốc), con số đã biết độc lập với code. `solve.csv` dòng 1, `tests/test_backtracking.py:158`.
6. **Vì sao alpha-beta thắng MCTS trong thí nghiệm — có phải MCTS yếu?**
   Không kết luận như vậy. Cùng wall-clock, MCTS Python chỉ đạt ~2–4 k sim/s (`bench_mcts.csv`: 1.7 k–4.4 k sim/s trên 9x9) còn AB ~9–10 k node/s với ordering giúp giảm node ~100×. Kết luận chỉ áp dụng cho cài đặt này; kiểm chứng bằng nodes_budget (chưa chạy FULL).
7. **Công bằng thế nào khi các agent dùng thời gian khác nhau?**
   Đo wall time từng nước, đếm vượt 1.5× budget; hiện 14/16 agent 0 %, 2 hybrid vi phạm 12–70 %, đang sửa (P0-2). Đổi màu và opening giống nhau cho mọi cặp. Dẫn chứng: `pilot_main/pilot/games.jsonl` (`wall_s`), `eval/tournament.py:222`.
8. **Hybrid MCTS_AB khác alpha-beta thuần thế nào, có phải mới?**
   Lá của cây MCTS được định giá bằng alpha-beta nông thay cho rollout, giá trị nén `(1−tanh(s/scale))/2`, kẹp ±0.999 để 0/1 nghĩa là chứng minh. Không phải mới (MCTS-minimax hybrids); đóng góp là so sánh có kiểm soát. Dẫn chứng: `agents/hybrid.py`, `PROGRESS.md` P5.
9. **Elo và khoảng tin cậy được tính thế nào, vì sao tin?**
   Bradley–Terry MLE, thêm 0.1 ván hòa ảo mỗi cặp để Elo hữu hạn khi bất bại, neo `random = 0`, bootstrap 95 % resample theo ván (không theo opening → hơi lạc quan). Kiểm tra: Elo tái tạo rating tổng hợp trong ±25 (1,500 ván/cặp) — `tests/test_eval.py`. Pilot CI ≈ ±200.
10. **Kiểm chứng thế nào rằng GUI/agent không làm hỏng bàn cờ?**
    Mọi agent có test "board unchanged" (`test_alphabeta.py:153`, test_mcts, test_hybrid) và `eval/tournament.py` assert hash/ply trước-sau mỗi nước, ném `RuntimeError("modified the board")`. GUI logic tách ở `gui/controller.py` có 20 test không cần pygame.

---

## 6. Giới hạn của chính bản audit này

- Không đọc/chạy lại toàn bộ code; các nhận xét về `agents/*`, `eval/*` dựa trên đọc có chọn lọc (dòng được trích) và tài liệu của nhóm.
- Không tự chạy lại các con số "block 20/20", throughput MCTS, puzzle accuracy — lấy từ `REPORT_FOR_TEAM.md`/CSV có sẵn và đã đánh dấu.
- Điểm số ở §0.1 là phán đoán của người chấm giả định, không phải kết quả đo.
- Chưa kiểm chứng: cài đặt từ venv sạch, biên dịch LaTeX, GUI chơi tay, đối chiếu (4,3)/(4,4) với tài liệu, độ chính xác của ước lượng 11x11.
