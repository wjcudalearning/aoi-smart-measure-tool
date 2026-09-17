# AOI 智慧尺寸量測與檢測系統 (現代化解耦任務引擎與完整後端矩陣)

本專案旨在將原 C# .NET Framework 4.7.2 WinForms AOI 系統（`AoiMeasureTool`）全面重構為基於 **Python 3.12+、PySide6 (Qt6)、GPU 加速 (CUDA / CuPy) 與動態可插拔算子引擎 (Pluggable Vision Task Engine)** 的工業級檢測軟體。

---

## 🎯 重構核心目標與解耦架構

1. **算子任務與管線徹底解耦 (Pluggable Vision Task Architecture)**：
   - 捨棄固定硬編碼的程序式流程，改採 **Blackboard 上下文模式 (`InspectionContext`)** 與 **動態任務鏈 (`list[VisionTask]`)**。
   - 所有視覺工具（前處理、定位、量測、瑕疵、評判、PLC輸出）皆為獨立可插拔的 Task，支援動態組合與自由擴充。
2. **五大後端基礎設施矩陣 (Full Backend Matrix)**：
   - **運算加速後端**：OpenCV-CUDA (`GpuMat`, Streams)、CuPy GPU 並行、CPU NumPy SIMD、ONNX Runtime。
   - **硬體相機驅動後端 (HAL)**：標準 OpenCV USB/DirectShow 相機、海康 (Hikrobot MVS)、巴斯勒 (Basler Pylon)、目錄模擬相機。
   - **工業自動化通訊後端**：Modbus TCP、TCP/IP ASCII Socket、硬體/軟體觸發排程器。
   - **生產歷史資料庫後端**：SQLite 非同步寫入佇列、CPK/良率分析、CSV/Excel 匯出。
   - **算子演算法庫後端**：單雙門檻形態學、基準角與模板匹配、直線/點線/圓孔擬合量測、瑕疵斑點分析、安全 AST 評判。
3. **現代化工業級 UI/UX (PySide6 / Qt6)**：
   - 硬體加速 Viewport (`QGraphicsView`) 支援 60FPS 平移縮放與多圖層疊加。
   - 3 通道即時檢測儀表板、動態算子調校工作區、歷史分析趨勢圖。

---

## 🏗️ 系統分層架構 (Target Architecture)

```text
aoi_system/
├── core/                           # 核心領域層 (純 Python / NumPy / Pydantic)
│   ├── models/                     # 資料實體 (幾何、配方、結果、公差)
│   ├── context.py                  # InspectionContext 黑板上下文
│   ├── coordinates.py              # 工件本體局部座標轉換 (ReferenceBasis)
│   └── logger.py                   # Loguru 集中非同步日誌
│
├── algorithms/                     # 核心演算法與運算後端
│   ├── backend/                    # 運算後端封裝 (NumPy / CuPy / OpenCV-CUDA / ONNX)
│   ├── preprocess/                 # 影像前處理濾波器 (CPU / GPU 雙實作)
│   ├── alignment/                  # 定位與配準 (基準角、旋轉矩形、模板匹配)
│   ├── measurement/                # 尺寸量測 (次像素直線、點線距、圓孔擬合)
│   ├── defect/                     # 表面瑕疵分析 (斑點分析 Blob、差分遮罩)
│   └── judgement/                  # 公差評判引擎 (安全 AST 表達式求值)
│
├── pipeline/                       # 檢測管線與任務調度 (Task Engine)
│   ├── tasks/                      # 算子任務抽象與實作 (Preprocess, Align, Measure, Judge, PLC)
│   ├── runner.py                   # 動態任務鏈執行器 (TaskPipelineRunner)
│   ├── slot_worker.py              # 獨立 Slot 背景工作執行緒與佇列隔離
│   └── orchestrator.py             # 3-Slot 連續檢測協調器
│
├── hardware/                       # 硬體設備抽象層 (HAL)
│   ├── camera_base.py              # 相機抽象介面 (CameraDevice)
│   ├── opencv_camera.py            # 標準 USB / DirectShow 相機驅動
│   ├── hikrobot_camera.py          # 海康 MVS SDK 相機驅動
│   ├── basler_camera.py            # 巴斯勒 Pylon SDK 相機驅動
│   └── simulated_camera.py         # 本機圖檔/合成訊號模擬相機
│
├── communication/                  # 工業通訊與觸發層
│   ├── modbus_client.py            # Modbus TCP 通訊客戶端 (PLC 互動)
│   ├── tcp_socket.py               # TCP/IP ASCII Socket 通訊服務端
│   └── trigger_dispatcher.py       # 硬體/軟體/網路觸發排程器
│
├── storage/                        # 持久化與歷史分析層
│   ├── database/                   # SQLite 非同步資料庫 (檢測歷程、良率、統計)
│   ├── recipe_repository.py        # 結構化動態配方儲存 (JSON)
│   ├── legacy_migrator.py          # 舊版 INI 轉換至動態任務鏈相容模組
│   └── exporter.py                 # CSV / Excel 報表匯出引擎
│
└── ui/                             # 表現層 (PySide6 / Qt6 MVVM)
    ├── components/                 # 通用元件 (QGraphicsView 視圖、KPI 卡片、權限切換)
    ├── viewmodels/                 # MVVM ViewModel 層
    └── views/                      # 檢視畫面 (即時檢測、算子調校、配方編輯、歷程分析)
```

---

## 📋 重構任務規劃清單 (TODO Checklist)

### 階段零：環境、標準與 CI/CD 基礎設施 (已完成 ✅)
- [x] 建立專案指南與架構原則 (`AGENTS.md`)
- [x] 建立專屬 Workspace Skills (`aoi-algorithm-benchmark`, `aoi-recipe-migrator`, `aoi-cuda-profiler`, `aoi-tdd-workflow`)
- [x] 建立 GitHub Actions CI 自動化工作流 (`.github/workflows/ci.yml`)
- [x] 建立專屬 Subagents (`algo_specialist`, `ui_ux_architect`, `qa_benchmark_agent`)
- [x] 建立虛擬環境與套件依賴 (`pyproject.toml`)

### 階段一：黑板上下文與動態任務管線引擎 (`pipeline.tasks` & `core.context`)
- [x] **黑板上下文架構 (`core.context.InspectionContext`)**
  - [x] 支援動態儲存原圖與各階段中間處理影像 (`images: dict[str, np.ndarray]`)
  - [x] 支援幾何特徵與座標基底註冊 (`features: dict[str, Any]`)
  - [x] 支援量測數值與公差判定收集 (`measurements: dict[str, float]`)
  - [x] 支援異常與日誌收集 (`anomalies: list[str]`)
- [x] **視覺算子任務抽象合約 (`pipeline.tasks.base.VisionTask`)**
  - [x] 定義標準 `execute(ctx: InspectionContext) -> TaskResult` 介面
  - [x] 支援任務啟用/禁用、執行耗時統計與例外捕獲
- [x] **任務註冊工廠 (`pipeline.tasks.registry.TaskRegistry`)**
  - [x] 支援透過類型字串動態反射實例化與註冊算子
- [x] **動態管線執行器 (`pipeline.runner.TaskPipelineRunner`)**
  - [x] 支援依序執行任意長度的自訂任務鏈 (`list[VisionTask]`)
  - [x] 提供前置攔截與後置檢查鉤子
- [x] **解耦動態配方實體 (`core.models.recipe.InspectionRecipe`)**
  - [x] 將配方定義重構為動態任務配置清單 (`tasks: list[VisionTaskConfig]`)
  - [x] 更新 `storage.legacy_migrator` 將舊版 INI 自動轉換為動態任務鏈


### 階段二：完整運算與 GPU 加速後端矩陣 (`algorithms.backend`)
- [x] **CPU NumPy SIMD 運算後端 (`NumPyCpuBackend`)**
  - [x] 跨平台通用運算降級路徑
- [x] **CuPy GPU 陣列運算後端 (`CuPyBackend`)**
  - [x] 支援 RTX 3090 GPU 記憶體並行加速
- [x] **OpenCV-CUDA 硬體加速後端 (`CudaOpenCVBackend`)**
  - [x] 封裝 `cv2.cuda.GpuMat`、Pinned Host Memory 與 CUDA Streams
  - [x] 實作 GPU 原生二值化、雙門檻分割與形態學開閉運算
- [x] **AI 推論後端 (`OnnxInferenceBackend`)**
  - [x] 支援 ONNX Runtime (CUDA / DirectML / CPU) 模型載入與推論

### 階段三：相機硬體驅動後端矩陣 (`hardware.drivers`)
- [x] **相機 HAL 統一抽象 (`hardware.camera_base.CameraDevice`)**
  - [x] 連接、斷開、單次取圖、非同步串流回呼標準化
- [x] **標準 OpenCV USB/DirectShow 相機 (`hardware.opencv_camera.OpenCvCameraDriver`)**
  - [x] 支援 Windows DirectShow / UVC 工業視訊相機
- [x] **海康機器人工業相機 (`hardware.hikrobot_camera.HikrobotCameraDriver`)**
  - [x] 封裝 MVS SDK / CTypes，支援曝光、增益、軟硬體觸發控制
- [x] **巴斯勒工業相機 (`hardware.basler_camera.BaslerCameraDriver`)**
  - [x] 封裝 Basler Pylon SDK，支援 GigE / USB3 相機連接與取圖
- [x] **本機模擬相機 (`hardware.simulated_camera.SimulatedCameraDriver`)**
  - [x] 支援目錄圖檔輪播、多格式讀取與合成瑕疵測試模式

### 階段四：工業通訊與 PLC 觸發排程後端 (`communication`)
- [ ] **Modbus TCP 工業通訊客戶端 (`communication.modbus_client.ModbusTcpClient`)**
  - [ ] 讀取 PLC 檢測就緒/觸發線圈 (Trigger Coil)
  - [ ] 寫入 A/B/NG 判定結果與產品計數暫存器 (Registers)
- [ ] **TCP/IP ASCII Socket 服務端 (`communication.tcp_socket.TcpSocketServer`)**
  - [ ] 支援標準產線機械手臂與自動化設備指令互動 (如 `START`, `TRIG`, `RESULT?`)
- [ ] **多來源觸發調度器 (`communication.trigger_dispatcher.TriggerDispatcher`)**
  - [ ] 統一排程軟體觸發、相機硬體 IO 觸發與 PLC 網路觸發

### 階段五：生產歷程資料庫與統計分析後端 (`storage.database`)
- [ ] **SQLite 非同步儲存後端 (`storage.database.sqlite_db.SqliteInspectionDatabase`)**
  - [ ] 建立工件檢測歷程資料表（時間戳記、產品型號、判定結果、各尺寸數值、圖檔路徑）
  - [ ] 實作非同步寫入佇列，保證高頻檢測下磁碟 I/O 零阻塞
- [ ] **品質統計與製程能力分析服務 (`storage.database.analytics.QualityAnalyticsService`)**
  - [ ] 計算即時良率 (Yield)、CPK、PPK、標準差與尺寸分佈長條圖
- [ ] **多格式報表匯出引擎 (`storage.exporter.ReportExporter`)**
  - [ ] 支援檢測記錄自訂欄位匯出為 CSV 與 Excel 格式

### 階段六：標準視覺算子庫 (Pluggable Vision Operators)
- [ ] **影像前處理算子 (`pipeline.tasks.PreprocessTask`)**
  - [ ] 支援多後端單門檻、雙門檻分割與自訂形態學組合
- [ ] **定位配準算子 (`pipeline.tasks.CornerAlignmentTask`, `TemplateMatchTask`)**
  - [ ] 基準角定位 (`ContourNearest`, `RoiTopEdge`, `ScanSearch`)
  - [ ] 模板匹配定位 (Normalized Cross-Correlation)
- [ ] **幾何尺寸量測算子 (`LineMeasureTask`, `PointToLineTask`, `CircleFitTask`)**
  - [ ] 次像素邊緣直線量測與平行/垂直投影距離
  - [ ] 點到直線最短距離量測
  - [ ] 最小平方法圓孔孔徑與同心度擬合 (Circle Fit)
- [ ] **表面瑕疵檢測算子 (`pipeline.tasks.BlobDefectTask`)**
  - [ ] 連通域面積、周長、圓度與深淺斑點瑕疵分析
- [ ] **安全公差評判算子 (`pipeline.tasks.ToleranceJudgementTask`)**
  - [ ] 基於安全 AST 求解各尺寸公差，執行 A/B/NG 階層判定
- [ ] **PLC 訊號發送算子 (`pipeline.tasks.PlcPublishTask`)**
  - [ ] 將當前結果自動透過通訊後端發布至外部產線設備

### 階段七：現代化 Studio UI 重構 (動態工作流與算子調試)
- [ ] **三通道即時檢測儀表板 (`ui.views.live_inspection_view`)**
  - [ ] 支援 3 Slot 獨立預覽、實時良率統計卡片、大字卡判定反饋
- [ ] **動態算子任務鏈視覺化工作區 (`ui.views.task_pipeline_view`)**
  - [ ] 支援在畫面上隨意新增、刪除、拖曳調整算子順序
  - [ ] 支援在視窗中即時查看任何算子產出的中間處理影像 (Intermediate Buffers)
- [ ] **歷史紀錄與品質分析看板 (`ui.views.history_view`)**
  - [ ] 查詢歷史檢測紀錄、統計圖表繪製、CSV/Excel 一鍵匯出
- [ ] **通訊設定與 I/O 監控視窗 (`ui.views.communication_view`)**
  - [ ] Modbus / Socket 連線狀態監控與手動觸發測試

### 階段八：整合測試、效能壓測與打包交付
- [ ] **全後端單元測試與 TDD 驗證** (維持覆蓋率 >= 80%)
- [ ] **高頻 60FPS 壓力測試與延遲基準驗證** (< 30ms 延遲)
- [ ] **Windows 獨立執行檔打包 (`scripts.build_exe`)**
- [ ] **一鍵啟動腳本與現場部署文件 (`run.bat`, `run.ps1`)**
