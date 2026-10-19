# RenderDoc Frame Debugger

GPU 프레임 캡처(`.rdc`)를 분석해 **1번째부터 N번째 DrawCall까지 누적된 화면**과 **해당 Draw가 사용하는 텍스처**를 함께 확인하는 Windows용 도구입니다. 화살표 키로 Draw를 이동하고 실행 직전/직후 화면을 비교할 수 있습니다.

## 설치 및 준비

| 목적 | 필요한 항목 |
| --- | --- |
| 기존 HTML 결과 열람 | JavaScript와 로컬 이미지 표시가 가능한 브라우저, 결과 HTML과 함께 생성된 `_assets` 폴더 |
| RDC 분석 | Windows x64, Windows PowerShell(`powershell.exe`), RenderDoc 전체 배포본, 캡처를 로컬 재생할 수 있는 GPU와 그래픽 드라이버, 브라우저 |
| 새 프레임 캡처 | RenderDoc으로 캡처할 수 있는 대상 프로그램과 그 실행 환경 |
| 선택적 개발 검증 | Node.js 또는 Python 3 + Pillow |

### RenderDoc 배치

RenderDoc Windows x64 전체 배포본을 준비해 아래 위치에 배치합니다. 바이너리는 이 저장소에 포함하지 않습니다.

```text
RenderDoc/PFiles/RenderDoc/
  qrenderdoc.exe
  renderdoccmd.exe
  renderdoc.dll
  renderdoc.json
  ...배포본에 포함된 Python / Qt / DLL / 플러그인 파일
```

실행 파일만 복사하지 말고 배포본 전체를 유지하세요. 분석 실행기는 위 경로를 사용하며 시스템에 설치된 RenderDoc을 자동으로 찾지 않습니다. GPU와 드라이버는 해당 캡처의 그래픽 API와 기능을 지원해야 합니다.

추출기는 `qrenderdoc.exe --python`으로 실행되므로 **일반 사용에는 별도 Python 설치나 `pip install renderdoc`이 필요하지 않습니다.** PowerShell 7, Node.js, npm 패키지, 웹 서버도 필수가 아닙니다. Windows PowerShell의 WinForms/.NET 기능을 사용하므로 대화형 Windows 환경에서 실행합니다.

프로젝트의 `output/`에 쓰기 권한과 충분한 디스크 공간이 필요합니다. 각 Draw의 전후 이미지를 캐시와 열람용 결과에 저장하므로 원본 RDC보다 많은 공간을 사용할 수 있습니다.

## 사용법

아래 명령은 프로젝트 루트의 PowerShell에서 실행합니다. 예제 파일 이름과 경로는 사용자가 준비한 캡처로 바꾸세요.

### 1. 캡처 준비

RenderDoc에서 대상 프로그램을 실행하고 원하는 프레임을 캡처합니다. 캡처 파일은 `output/captures/` 아래에 보관하면 Git에서 제외됩니다. 기본 캡처 단축키가 변경되지 않은 환경에서는 F12를 사용할 수 있습니다.

대상 프로그램의 실행 파일, 작업 디렉터리, 실행 인자 등은 각 환경에 맞게 설정합니다. 개인 환경의 실행 배치나 프로젝트별 캡처 스크립트는 공개 저장소에 포함하지 않습니다.

### 2. RDC 분석

파일 선택창으로 캡처를 고릅니다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\rdc_viewer.ps1
```

캡처 경로를 직접 지정할 수도 있습니다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\rdc_viewer.ps1 -CapturePath .\output\captures\frame.rdc
```

추출이 끝나면 기본 브라우저에 결과를 엽니다. 브라우저 열기만 생략하려면 `-NoOpen`을 추가합니다. 이 옵션에서도 진행창과 오류 대화상자는 사용합니다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\rdc_viewer.ps1 -CapturePath .\output\captures\frame.rdc -NoOpen
```

첫 분석은 캡처 규모에 따라 시간이 걸립니다. 이후에는 유효한 추출 캐시를 재사용합니다. 실행이 끝나면 결과 HTML의 경로를 출력합니다.

### 3. DrawCall별 결과 확인

왼쪽은 Draw 목록, 가운데는 렌더 결과, 오른쪽은 해당 Draw가 읽는 텍스처입니다.

| 조작 | 기능 |
| --- | --- |
| `←` / `↑` | 이전 Draw |
| `→` / `↓` | 다음 Draw |
| `Home` / `End` | 첫 번째 / 마지막 Draw |
| 목록 클릭 | 선택한 Draw로 이동 |
| Draw 번호 입력 후 Enter 또는 입력 확정 | 지정한 N번째 Draw로 이동 |
| 슬라이더 | 누적 Draw 수 변경 |
| **누적 결과** | 선택한 Draw까지 실행한 결과 |
| **이번 Draw 직전** | 선택한 Draw 바로 전 이벤트까지 실행한 결과 |
| 출력 선택창 | 여러 색상 렌더 타깃 중 표시할 출력 선택 |
| 가운데 결과 이미지 클릭 | 원본 크기로 열기 |
| 검색창 | Draw 번호, Event 번호, 호출 이름, 텍스처 ID/이름으로 검색 |

예를 들어 총 170 Draw인 캡처에서 Draw 50을 선택하면 해당 시점까지 실행된 결과가 나옵니다. **이번 Draw 직전**과 **누적 결과**를 번갈아 누르면 50번째 호출이 화면에 추가한 내용을 비교할 수 있습니다. 오른쪽에는 해당 호출이 읽는 텍스처 이미지, 크기, 포맷, 셰이더 슬롯을 표시합니다. 작은 내부 텍스처는 접힌 항목에 모았습니다.

입력창·슬라이더·출력 선택에 포커스가 있으면 화살표는 해당 입력의 기본 동작을 사용합니다. Draw 이동 단축키를 사용하려면 입력 외 영역을 클릭하세요. 검색 중에도 단축키는 검색 결과가 아닌 전체 Draw 순서를 따릅니다.

## 결과 해석과 현재 범위

- 가운데 화면은 **현재 Draw가 쓰는 색상 렌더 타깃**입니다. 중간 버퍼, 효과, 최종 합성 단계를 거치면 표시 대상의 ID가 바뀔 수 있습니다.
- 앞선 Clear·Copy 명령도 실제 재생 순서에 포함합니다. Draw 번호는 DrawCall만 세므로 Event 번호와 다릅니다.
- 직전 화면은 이전 Draw 이미지를 재사용하지 않고 이번 Draw 바로 전 이벤트까지 별도로 재생합니다.
- 가려진 도형, 화면 밖 작업, 같은 값 덮어쓰기 등으로 Draw가 증가해도 눈에 보이는 변화가 없을 수 있습니다. 색상 출력이 없는 Draw는 안내 문구를 표시합니다.
- 가운데 결과 이미지는 RGB 확인을 위해 알파를 제거해 표시하고, 오른쪽 사용 텍스처는 알파를 보존합니다.
- 프레임 도중 수정되는 사용 텍스처는 쓰기 이벤트별로 저장합니다.
- 텍스처 목록은 현재 Fragment 셰이더의 읽기 전용 이미지 바인딩을 대상으로 합니다. 모든 셰이더 단계·버퍼·컴퓨트 작업을 보여주는 UI는 아닙니다.
- Godot 노드 이름과 `AtlasTexture` 원본 사각형은 현재 추출 정보에 포함되지 않습니다. 아틀라스 전체가 표시되고 GPU 리소스 이름이 보일 수 있습니다.
- 한 프레임 안의 명령 순서를 탐색합니다. 여러 시간대의 프레임을 영상처럼 재생하는 기능은 없습니다.

## 파일 구조와 개인정보 제외

```text
export_capture.py              # RenderDoc GPU 재생 / 이미지 추출
frame_viewer_template.html      # 브라우저 뷰어
rdc_viewer.ps1                  # 분석 실행 / 캐시 관리 / HTML 생성
tests/                         # 선택적 검증 스크립트
RenderDoc/                     # 사용자가 배치하는 실행 환경, Git 제외
output/                        # 로컬 조사 결과 전체, Git 제외
  captures/                    # 원본 RDC 및 기존 분석 결과
  viewer_cache/<키>/            # 추출 JSON, 이미지, 상태, 캐시 정보
  results/<키>/
    frame.html
    frame_assets/
      frames/                  # Draw 직전/직후 이미지
      textures/                # 사용 텍스처
  verification/                # 검증용 미리보기
```

분석 결과와 캐시는 입력 RDC가 외부 경로에 있어도 `output/` 아래에 생성합니다. 캡처 경로별 키를 사용해 이름이 같은 캡처의 결과를 구분합니다. 캐시에는 원본 경로 등 로컬 정보가 들어갈 수 있으므로 커밋하지 않습니다.

`.gitignore`는 `output/`, RenderDoc 배포본, `.rdc`, 추출 이미지 폴더, 개인 실행 배치(`.bat` / `.cmd`)와 프로젝트 전용 캡처 스크립트를 제외합니다. 다른 프로그램으로 저장한 조사 결과도 `output/` 안에 두세요. README에는 특정 PC의 조사 결과·샘플 정보·개인 경로를 기록하지 않습니다.

결과만 전달하려면 HTML과 같은 이름의 `_assets` 폴더를 함께 복사하고 상대 위치를 유지합니다. 열람에는 원본 RDC나 RenderDoc이 필요하지 않습니다. 이미지 자체에 대상 프로그램의 정보가 포함될 수 있으므로 전달 범위는 직접 확인하세요.

캐시는 캡처 경로·크기·수정 시각과 추출기 해시로 재사용 여부를 판단합니다. 강제 재추출은 분석이 실행 중이지 않을 때 해당 캐시의 `manifest.json`을 삭제하고 다시 실행합니다. 캐시 폴더를 지워도 별도로 보관한 원본 RDC는 남습니다.

## 문제 해결

| 증상 | 확인 방법 |
| --- | --- |
| 필요한 실행 파일/DLL이 없음 | RenderDoc 전체 배포본을 지정 경로에 배치했는지 확인합니다. |
| PowerShell 실행 정책 오류 | 위 명령을 사용합니다. 조직 정책으로 제한된 환경은 관리자에게 확인합니다. |
| 캡처 재생/분석 실패 | 오류 대화상자와 `output/viewer_cache/<키>/status.txt`를 확인합니다. GPU/드라이버 지원 여부와 RenderDoc에서 원본을 직접 재생할 수 있는지 확인합니다. |
| 분석이 오래 걸림 | 캐시의 `frames` 이미지가 늘어나는지, 디스크 공간이 충분한지 확인합니다. |
| 결과에 이미지가 없음 | HTML과 `_assets` 폴더가 함께 있는지, 브라우저가 로컬 이미지와 스크립트를 표시하는지 확인합니다. 필요하면 다시 분석합니다. |
| 화살표로 Draw가 이동하지 않음 | 입력창이나 선택창에서 포커스를 뺀 뒤 다시 시도합니다. |
| Draw를 넘겨도 같은 화면 또는 검은 화면 | 출력 Target ID와 직전/직후 화면을 확인합니다. 중간 버퍼이거나 표시 픽셀에 변화가 없는 호출일 수 있습니다. |
| 변경한 뷰어 UI가 보이지 않음 | 새 템플릿으로 분석 실행기를 다시 실행하고 생성된 HTML을 엽니다. |

## 개발용 검증 — 선택 사항

분석된 HTML 경로를 인자로 전달합니다. 일반 사용에는 아래 도구 설치가 필요하지 않습니다.

Node.js가 설치되어 있으면 외부 npm 패키지 없이 조작 로직을 검증할 수 있습니다.

```powershell
node .\tests\viewer_smoke.cjs '<결과 HTML 경로>'
```

Python 3와 Pillow로 이미지 누락, 전후 크기, 화면 변화를 확인하고 `output/verification/draw_progression.jpg`를 생성할 수 있습니다.

```powershell
python -m pip install Pillow
python .\tests\verify_capture.py '<결과 HTML 경로>'
```

조작 검증은 DOM 모형을 사용하며 실제 브라우저의 배치나 클릭 동작을 검증하지는 않습니다.
