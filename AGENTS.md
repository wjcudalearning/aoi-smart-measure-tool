# AOI 智慧量測與檢測系統 - Agent 指南 (AGENTS.md)

本文件為 AI Agent 與開發者在此專案進行協同開發的**最高準則與規範**。所有在此專案工作的 Agent 均需遵守以下架構原則、代碼規範與協作流程。

---

## 🧭 專案全貌與核心任務

- **領域**：工業自動化光學檢測 (AOI, Automated Optical Inspection) - 尺寸量測與公差判定系統。
- **目標**：從原 C# .NET Framework 4.7.2 WinForms 舊架構，重構為基於 **Python 3.12+、PySide6 (Qt6) 與 GPU 加速 (CuPy / OpenCV-CUDA)** 的現代化高效能系統。
- **硬體基底**：NVIDIA GeForce RTX 3090 (24GB VRAM)，支援高頻多相機即時檢測。
- **關鍵任務**：
  1. 徹底解耦 UI 與核心演算法（遵循 Clean Architecture / DDD / MVVM）。
  2. 善用 GPU 加速影像前處理（二值化、雙門檻、形態學）。
  3. 100% 保持並驗證核心演算法精度（基準角定位、局部座標投影、平行/垂直距離量測、A/B/NG 判定）。
  4. 重塑現代化、流暢 (60FPS) 且具工業質感的 UI/UX。

---

## 🏛️ 架構規範 (Architecture & OOP Guidelines)

### 1. 模組分層與單向依賴
嚴格禁止 UI 層與演算法層循環依賴。系統依照以下分層單向依賴：
```text
UI (Views / ViewModels) ──► Pipeline (Orchestrator) ──► Core (Domain & Algorithms)
                                                      ──► Storage (Repository)
                                                      ──► Hardware (Camera HAL)
```
- **`core/`**：領域模型與座標幾何轉換，純 Python/NumPy，**絕不可引入 PySide6 或 UI 元件**。
- **`algorithms/`**：影像前處理、基準角定位、邊緣尋找與量測。提供抽象介面，支援 GPU (CuPy) 與 CPU (NumPy) 自動降級後端。
- **`hardware/`**：相機硬體抽象層 (HAL)，對外提供一致的影像擷取串流介面。
- **`pipeline/`**：3 通道獨立 Slot 佇列管理與非同步協調器，保持記憶體零複製 (Zero-Copy)。
- **`storage/`**：配方管理 (SQLite / JSON) 與舊版 INI 遷移模組。
- **`ui/`**：PySide6 表現層，採用 MVVM 模式，透過 Signals/Slots 與 ViewModel 溝通。

### 2. 避免 God Object (上帝物件)
- 嚴禁出現像 C# `MainForm` 一樣超過數千行的萬能類別。
- 單一類別行數建議控制在 300~500 行內，每個模組僅專注單一職責 (Single Responsibility Principle)。

---

## ⚡ 效能與 GPU 加速準則 (Performance & Concurrency)

1. **GPU/CPU 雙後端容錯**：
   - 影像前處理運算應優先使用 GPU（CuPy / cv2.cuda），若環境無 CUDA 支援，需無縫切換至 CPU (NumPy)，不可崩潰。
2. **零硬碟 I/O 快速通道**：
   - 相機輸入之 Frame 在記憶體中直接傳遞運算，嚴禁寫入暫存圖檔再讀取的反模式。
3. **UI 執行緒零阻塞**：
   - 所有影像處理、相機取圖、磁碟儲存必須在背景工作執行緒（`QThreadPool` 或 `QThread`）執行。
   - 繪圖預覽應採用 `QGraphicsView` / `QOpenGLWidget` 進行硬體加速渲染。

---

## 📐 核心領域知識與術語 (Domain Terminology)

- **基準角 (Reference Corner)**：工件在影像中的定位特徵點（含頂點、方向角度與旋轉矩形），用於建立工件本體座標系。
- **ReferenceBasis**：工件局部座標系基底（Anchor, UnitX, UnitY），用於消除工件在治具上的平移與旋轉偏移。
- **Local Coordinates (局部座標)**：相對於基準角基底的正規化座標。配方中所有量測起訖點均以局部座標儲存。
- **平行量測 (Parallel) / 垂直量測 (Perpendicular)**：分別代表沿工件基準線方向或法線方向投影的精確距離。
- **3-Slot Continuous Inspection**：系統具備 3 個獨立檢測通道，各通道可綁定不同相機、子參數與配方，支援高頻獨立判定。
- **A / B / NG 判定分級**：
  - `A`：所有量測項目皆符合 A 規。
  - `B`：存在項目落入 B 規，且無任何項目落入 C 規。
  - `NG`：任何項目落入 C 規。

---

## 🛠️ 開發與代碼品質規範 (Code Style)

1. **語言環境**：Python 3.12+，套件管理器統一使用 `uv`。
2. **型別提示**：所有函式與方法必須具備完整的 Type Hints（使用 `typing` / Python 3.12 原生型別）。
3. **資料校驗**：領域實體統一採用 `Pydantic v2` 或 `dataclass`。
4. **字元編碼**：
   - 所有 Python 檔案一律採用 `UTF-8`。
   - 若因相容性需讀寫或修改 C# 舊專案字串檔案，務必維持 `UTF-8 with BOM`。
5. **TDD 測試驅動開發規範 (Test-Driven Development)**：
   - 遵循 **Red-Green-Refactor** 流程：實作或移植任何領域邏輯/演算法前，**必須先寫測試 (Test-First)**。
   - 演算法精度標準：新演算法與 C# 基準數值的輸出誤差嚴格控制在 $0.001\text{ mm}$ 以內。
   - 測試覆蓋率底線：全專案單元測試覆蓋率必須維持在 **85% 以上** (`pytest --cov-fail-under=80`)。
6. **CI/CD 自動化檢查準則**：
   - 所有 Push / PR 均會觸發 GitHub Actions CI，包含 Ruff 程式碼檢查、Mypy 靜態型別分析與 Pytest 矩陣測試。
   - 嚴禁破壞既有測試，CI 必須維持綠燈方可合併。

---

## 🤖 專屬 Subagent 分工指引

在執行複雜子任務時，可指派以下角色的專屬 Subagent：

| Subagent 角色名稱 | 核心職責 | 專長領域 |
| :--- | :--- | :--- |
| **`algo_specialist`** | 負責 `algorithms/` 模組移植與調校 | OpenCV、CuPy、GPU 核心優化、次像素邊緣定位、旋轉矩形座標變換 |
| **`ui_ux_architect`** | 負責 `ui/` 模組開發與現代化重塑 | PySide6 (Qt6)、QGraphicsView、QSS 暗色工業主題、響應式佈局 |
| **`qa_benchmark_agent`** | 負責測試套件、黃金樣本驗證與效能監控 | pytest、數值精確度驗證、FPS/Latency 壓力測試、C# 輸出對比 |
| **`recipe_migrator`** | 負責 INI 檔案解析與新版配方存儲 | INI 解析、SQLite、JSON Schema、相容性遷移驗證 |
