# AOI 智慧尺寸量測與檢測系統 (Python 重構規劃)

本專案旨在將原 C# .NET Framework 4.7.2 WinForms AOI 系統（`AoiMeasureTool`）全面重構為基於 **Python 3.10+、PySide6 (Qt6) 與 GPU 加速** 的現代化工業級檢測軟體。

---

## 🎯 重構核心目標

1. **架構重塑 (Clean OOP / DDD / MVVM)**：
   - 徹底打破原 C# `MainForm` 超過 7,000 行的「上帝物件 (God Object)」結構。
   - 將 **演算法 (Algorithms)**、**業務領域 (Domain/Core)**、**相機硬體抽象 (Hardware/Camera)**、**配方儲存 (Persistence)** 與 **介面展示 (UI/UX)** 完全解耦。
2. **GPU 加速與高吞吐量 (GPU Acceleration & High Throughput)**：
   - 支援 GPU 影像前處理（二值化、雙門檻分割、形態學運算、邊緣提取）。
   - 採用 **CUDA / CuPy / OpenCV-CUDA / ONNX Runtime (DirectML/CUDA)** 雙後端（具備 GPU 加速時自動啟用，無 GPU 時無縫退回 CPU/NumPy）。
3. **現代化工業級 UI/UX (Modern Industrial UI)**：
   - 基於 **PySide6 (Qt 6)** + 現代暗色工業風格（如 QFluentWidgets / Modern Dark）。
   - 採用 `QGraphicsView` / `QOpenGLWidget` 實現硬體加速的超流暢百萬級像素平移、縮放、ROI 拖拉與即時量測標註 (Overlay)。
   - 改善操作員/工程師/管理者的切換體驗與配方 (Recipe) 編輯工作流。
4. **模組演算法完整繼承與強化 (Algorithm Preservation & Enhancement)**：
   - 完整移植並單元測試化驗證原系統的精華演算法：**基準角特徵定位 (`ReferenceBasis`)**、**工件本體局部座標轉換**、**平行/垂直量測線投影**、**A/B/NG 公差評級引擎**。

---

## 🏗️ 系統分層架構 (Target Architecture)

```text
aoi_system/
├── core/                       # 核心領域層 (純 Python / NumPy，無 UI 相依)
│   ├── models/                 # 資料實體 (Recipe, MeasureRecord, JudgementRule, etc.)
│   ├── coordinates.py          # 工件局部座標系轉換 (ReferenceBasis, 仿射變換)
│   └── events.py               # 事件匯流排 / 訊號定義
│
├── algorithms/                 # 核心影像處理與量測演算法 (支援 GPU/CPU 雙模式)
│   ├── backend/                # 運算後端封裝 (NumPy / CuPy / cv2.cuda)
│   ├── preprocess/             # 影像前處理 (二值化、雙門檻、形態學開閉膨脹侵蝕)
│   ├── corner_detection/       # 基準角定位 (輪廓、RotatedRect、邊緣掃描、突起模式)
│   ├── measurement/            # 尺寸量測 (次像素邊緣檢測、垂直/平行距離投影計算)
│   └── judgement/              # 公差評判引擎 (安全 AST 表達式求值、A/B/NG 規則)
│
├── hardware/                   # 硬體設備抽象層 (HAL)
│   ├── camera_base.py          # 相機抽象介面
│   ├── opencv_camera.py        # 虛擬/檔案/USB 相機
│   └── gige_camera.py          # 工業 GigE / USB3 相機 (如 Basler, Hikvision 等 SDK 介接)
│
├── pipeline/                   # 檢測管線與排程 (Multi-slot Concurrency)
│   ├── inspection_worker.py    # 獨立 Slot 檢測工作執行緒
│   ├── queue_manager.py        # 無鎖/安全佇列管理
│   └── orchestrator.py         # 連續檢測協調器 (3-Slot 並行處理)
│
├── storage/                    # 持久化層
│   ├── config_manager.py       # 系統全域設定 (YAML / JSON)
│   ├── recipe_repository.py    # 配方管理 (SQLite / JSON)
│   └── legacy_migrator.py      # 原 .ini (setting.ini, parameterReferenceList.ini) 轉換工具
│
└── ui/                         # 表現層 (PySide6 / Qt6)
    ├── components/             # 通用元件 (QGraphicsView 視窗、自訂滑桿、數值顯示卡)
    ├── viewmodels/             # MVVM ViewModel 層 (狀態與事件繫結)
    ├── views/                  # 畫面檢視
    │   ├── main_window.py      # 主視窗與現代化側欄導航
    │   ├── live_inspection.py  # 3-Slot 連續檢測工作區
    │   ├── recipe_editor.py    # 檢測配方與主/子參數關聯編輯
    │   ├── preprocess_view.py  # 影像前處理調校 (即時視覺化直方圖與效果)
    │   ├── corner_view.py      # 基準角標定工作區
    │   └── measure_view.py     # 量測線標定與多圖確認
    └── resources/              # 樣式表 (QSS)、圖標 (Icons)、字型
```

---

## 📋 重構任務規劃清單 (TODO Checklist)

### 階段零：Agent 協同基礎設施建置 (已完成 ✅)
- [x] **建立專案頂層指南 (`AGENTS.md`)**：規範架構分層、OOP 原則、GPU 雙後端策略、程式風格與名詞定義。
- [x] **建立專屬 Workspace Skills (`.agents/skills/`)**：
  - [x] `aoi-algorithm-benchmark`：演算法精度微米級比對與 CPU/GPU 效能基準測試。
  - [x] `aoi-recipe-migrator`：舊版 C# INI 配方解析、校驗與現代化結構轉換。
  - [x] `aoi-cuda-profiler`：RTX 3090 GPU 環境診斷、VRAM 監控與延遲分析。
  - [x] `aoi-tdd-workflow`：TDD (Red-Green-Refactor) 測試驅動開發標準流程。
- [x] **建立 GitHub Actions CI 自動化工作流 (`.github/workflows/ci.yml`)**：
  - [x] 涵蓋 Ubuntu / Windows 雙平台矩陣測試。
  - [x] 整合 Ruff (代碼格式/檢查)、Mypy (型別檢查) 與 Pytest (涵蓋率 >= 80% 門檻)。
- [x] **建立專屬 Subagents**：
  - [x] `algo_specialist`：演算法與 GPU/CUDA 加速專家。
  - [x] `ui_ux_architect`：PySide6 現代 UI 與硬體加速 Viewport 設計師。
  - [x] `qa_benchmark_agent`：數值精度與壓力測試工程師。

### 階段一：底層架構設計與基礎設施建置 (Foundation & Clean Architecture)
- [x] **環境與相依套件設定**
  - [x] 建立 `pyproject.toml` (相依：`pyside6`, `opencv-python`, `numpy`, `pydantic`, `pytest`, `pytest-cov`, `loguru`)
  - [x] 建立 `.venv` 虛擬環境並安裝完整相依環境
  - [x] 規劃 CPU / GPU 自動偵測切換機制（偵測 CUDA 可用性，自動選用 CuPy 或 NumPy） (`algorithms.backend.manager`)
- [x] **領域資料模型設計 (`core.models`)**
  - [x] 定義強型別資料類別 (`Pydantic v2`)：
    - [x] `Point2D`, `Point2I`, `ReferenceBasis`, `BoundingRect`, `RotatedRect`
    - [x] `MeasureRecord`（起訖點、局部座標、量測方向、公差）
    - [x] `ReferenceCornerSnapshot`（ROI、演算法模式、頂點、方向角）
    - [x] `PreprocessSnapshot`, `DualThresholdSnapshot`（單/雙門檻值、形態學運算參數）
    - [x] `JudgementCriterionRule`（A/B/NG 規則、表達式、上下限規格）
    - [x] `InspectionRecipe`（完整產品檢測配方）
    - [x] `CameraCalibration`（CCD X/Y 精度、物理縮放係數）
    - [x] `ContinuousInspectionResult`, `ContinuousInspectionRuleResult`（檢測結果實體）
  - [x] 實作工件局部座標系轉換 (`core.coordinates`) 並以 TDD 測試通過 (涵蓋率 99%)
- [x] **配方持久化與舊版 INI 相容工具 (`storage`)**
  - [x] 採用現代結構化儲存格式（JSON），取代雜亂的 INI 檔案 (`storage.recipe_repository`)
  - [x] 撰寫 `legacy_migrator.py`：能自動讀取原系統的 `setting.ini`、`parameterReferenceList.ini`、`innerSetting.ini`，一鍵匯入為新系統配方 (單元測試涵蓋率 94%)

---

### 階段二：核心演算法移植、優化與 GPU 加速 (Algorithms & Acceleration)
- [x] **影像前處理模組 (`algorithms.preprocess`)**
  - [x] 實作純 NumPy/OpenCV CPU 處理管線 (`algorithms.preprocess.filters`)
  - [x] 實作 CuPy / OpenCV CUDA GPU 加速管線（雙門檻分割、二值化、形態學開/閉/膨脹/侵蝕）
  - [x] 撰寫單元測試比對 CPU 與 GPU 運算輸出的一致性 (`tests.test_algorithms.test_preprocess`)
- [x] **基準角定位演算法 (`algorithms.corner_detection`)**
  - [x] 移植原輪廓極值點搜尋法 (`ContourNearest`)
  - [x] 移植旋轉矩形擬合與頂點解算 (`RotatedRect` / OpenCV `minAreaRect`)
  - [x] 移植邊緣掃描與突起特徵定位演算法 (`ScanSearch` / `ProtrusionMode`)
  - [x] 實作基準角局部座標系轉換器 (`ReferenceBasis` 向量投影，實現平移與旋轉不變性)
- [ ] **尺寸量測與邊緣搜尋模組 (`algorithms.measurement`)**
  - [ ] 實作給定兩點或局部座標的邊緣梯度搜尋（次像素邊緣偵測）
  - [ ] 實作「平行量測 (Parallel)」與「垂直量測 (Perpendicular)」投影距離計算法
  - [ ] 整合 CCD X/Y 精度校準與 Scale Factor，輸出真實物理量（mm / μm）
- [ ] **公差評級與判定引擎 (`algorithms.judgement`)**
  - [ ] 捨棄舊版不安全的字串計算，改以 Python `ast` (抽象語法樹) 安全解析公差計算式
  - [ ] 實作 A/B/NG 階層判定邏輯（全部符合 A 則為 A；含 B 且無 C 則為 B；含 C 則為 NG）
- [ ] **演算法單元測試與黃金樣本比對 (Golden Sample Validation)**
  - [ ] 建立測試資料集，將 C# 原系統的量測數值與 Python 運算結果對齊，確保精度誤差在容許微米範圍內

---

### 階段三：相機介接與多通道平行檢測管線 (Pipeline & Concurrency)
- [ ] **硬體抽象介面 (HAL)**
  - [ ] 定義統一生產者介面 (`CameraDevice`：連接、斷開、取圖、非同步回呼)
  - [ ] 實作本機影像目錄模擬相機（用於離線開發與驗證）
  - [ ] 預留主流工業相機 SDK 介面 (如 Hikrobot MVS、Basler Pylon 等)
- [ ] **三通道獨立非同步排程管線 (`pipeline.orchestrator`)**
  - [ ] 徹底落實 3 個 Slot 的執行緒/處理程序隔離：
    - Slot 0 / Slot 1 / Slot 2 各自擁有獨立的工作佇列與上下文 (`InspectionContext`)
    - 支援高頻相機連續送圖，同通道依序排隊，不同通道平行檢測
  - [ ] 實作記憶體零複製 (Zero-Copy) 共享與生命週期管理
  - [ ] 實作非同步原圖背景存檔（可開關，依 Slot 分目錄存檔）

---

### 階段四：現代化 UI/UX 重新設計 (Modern PySide6 Desktop UI)
- [ ] **視覺風格與佈局基礎**
  - [ ] 引進現代工業暗色主題 (Dark Theme) 與響應式佈局 (無縫支援 1080P/2K/4K 螢幕)
  - [ ] 現代側欄導覽列 (支援圖標 + 文字折疊、工作區直覺切換)
  - [ ] 權限模式與快速切換 (操作員 / 工程師 / 管理者，具備流暢的角色狀態切換與安全認證)
- [ ] **高效能影像檢視器元件 (`QGraphicsView` / OpenGL)**
  - [ ] 實作平滑如絲的滑鼠滾輪縮放 (Zoom) 與左鍵拖曳平移 (Pan)
  - [ ] 實作多層圖層架構 (底圖層、基準角標記層、ROI 選擇層、量測線層、公差標籤層)
  - [ ] 支援互動式 ROI 拖曳、量測點直覺微調
- [ ] **3-Slot 連續檢測儀表板 (Live Inspection View)**
  - [ ] 3 個獨立預覽卡片，支援實時 FPS、佇列狀態、量測耗時顯示
  - [ ] 即時良率統計圓餅圖/長條圖 (Total / A規 / B規 / NG 統計)
  - [ ] 判定結果大字卡即時視覺反饋 (綠色 A / 橙色 B / 紅色 NG)
- [ ] **配方與演算法調校工作區**
  - [ ] 前處理可視化工作區：即時雙門檻滑桿拖拉，即時預覽二值化與形態學效果
  - [ ] 基準角標定工作區：可視化微調 ROI 與掃描門檻，即時預覽旋轉框與錨點
  - [ ] 量測設定工作區：點選即可新增線段，彈出式平行/垂直輔助設定
  - [ ] 批次多圖驗證工作區：支援讀取目錄多張圖片快速走查，批次輸出量測 CSV 報告

---

### 階段五：整合測試、效能調優與打包發布 (Testing, Profiling & Deployment)
- [ ] **效能 Profiling 與調優**
  - [ ] 測試相機 30FPS / 60FPS 輸入下的 CPU/GPU 使用率
  - [ ] 確保 UI 介面在連續高頻檢測下維持 60FPS 零卡頓
- [ ] **打包與環境封裝**
  - [ ] 撰寫一鍵啟動腳本與 Conda/venv 環境鎖定檔
  - [ ] 使用 PyInstaller / Nuitka 進行獨立執行檔 (Standalone Exe) 打包
  - [ ] 建立日誌系統 (Loguru)，記錄檢測異常、量測超差紀錄與相機斷線自動重連

---

## 💡 技術選型建議 (Tech Stack)

| 模組領域 | 推薦技術 | 選型優勢 |
| :--- | :--- | :--- |
| **GUI 框架** | `PySide6` (Qt 6) + `QFluentWidgets` | 官方 Qt 綁定，穩定、硬體加速視窗、現代化工業美觀 UI |
| **GPU 加速運算** | `CuPy` + `OpenCV-CUDA` (或 `DirectML`) | 語法與 NumPy 高度相容，門檻低且在矩陣與影像濾波上具備數倍至數十倍效能提升 |
| **影像處理** | `OpenCV (cv2)` + `NumPy` | 成熟的電腦視覺工業標準，便於移植原 C# OpenCvSharp 演算法 |
| **非同步與平行處理** | `concurrent.futures` + Qt `QThreadPool` / `QThread` | 兼顧執行緒安全與事件驅動，避免 UI 執行緒被大量運算卡死 |
| **資料校驗與模型** | `Pydantic v2` / `dataclasses` | 強型別、自動資料驗證與 JSON 序列化，徹底取代鬆散的 INI 解析 |
| **日誌與監控** | `loguru` | 開箱即用、支援非同步寫入、自動依日期輪轉 |
