# Multi-Agent Research Lab

---

**Họ tên:** Nguyễn Thị Quỳnh Trang
**MSHV:** 2A202600406

---

Hệ thống nghiên cứu đa tác tử (multi-agent) dùng để so sánh trực tiếp giữa:
- **Single-agent baseline** (một lần gọi LLM),
- **Multi-agent workflow** (Supervisor điều phối Researcher, Analyst, Writer).

Project đã được triển khai hoàn chỉnh theo hướng production-demo: có orchestration, shared state, tracing, benchmark và báo cáo markdown.

---

## 1) Giới thiệu

### Project này là gì?
Đây là một research assistant có khả năng nhận query, thu thập thông tin, phân tích và viết câu trả lời cuối cùng.

### Giải quyết bài toán gì?
Các query nghiên cứu phức tạp thường cần nhiều bước:
- tìm nguồn,
- tổng hợp ghi chú,
- đánh giá độ mạnh bằng chứng,
- viết câu trả lời có dẫn nguồn.

### Khác biệt giữa single-agent và multi-agent
- **Single-agent**: nhanh, đơn giản, ít overhead.
- **Multi-agent**: có cấu trúc hơn, dễ trace/debug, kiểm soát chất lượng tốt hơn.

---

## 2) Kiến trúc hệ thống

### Flow chính
`User → Supervisor → Researcher → Analyst → Writer → Final Answer`

### ASCII architecture

```text
+------------------+      +------------------+
|      User        | ---> |    Supervisor    |
+------------------+      +------------------+
                                 |
                                 v
                         +------------------+
                         |    Researcher    | -- SearchClient + LLMClient
                         +------------------+
                                 |
                                 v
                         +------------------+
                         |     Analyst      | -- LLMClient
                         +------------------+
                                 |
                                 v
                         +------------------+
                         |      Writer      | -- LLMClient
                         +------------------+
                                 |
                                 v
                         +------------------+
                         |   Final Answer   |
                         +------------------+
```

### Vai trò từng agent
- **Supervisor**
  - Quyết định route tiếp theo: `researcher` / `analyst` / `writer` / `done`.
  - Áp dụng guardrail `MAX_ITERATIONS`.
  - Dừng an toàn khi lỗi tích lũy quá nhiều.
- **Researcher**
  - Lấy query từ state.
  - Gọi SearchClient để lấy nguồn (Tavily nếu có key, mock deterministic nếu không).
  - Gọi LLMClient để tạo `research_notes`.
- **Analyst**
  - Dựa trên `research_notes` + `sources` để tạo `analysis_notes`:
    - key claims,
    - evidence strength,
    - missing information,
    - comparison of viewpoints.
- **Writer**
  - Dựa trên `research_notes`, `analysis_notes`, `sources` để tạo `final_answer`.
  - Đảm bảo câu trả lời có source reference/citation.

### Shared state (ResearchState)
Mọi agent cùng đọc/ghi một state thống nhất, bao gồm:
- `request`, `sources`, `research_notes`, `analysis_notes`, `final_answer`
- `route_history`, `next_route`, `iteration`
- `trace`, `errors`
- usage/cost: `total_input_tokens`, `total_output_tokens`, `estimated_cost_usd`
- thời gian: `started_at`, `completed_at`

---

## 3) Cấu trúc thư mục

```text
src/multi_agent_research_lab/
  agents/         # Logic từng agent: supervisor/researcher/analyst/writer
  core/           # Config, schemas, state, errors
  services/       # LLM client, search client, storage
  graph/          # Workflow orchestration (build/run)
  evaluation/     # Benchmark + render markdown report
  observability/  # Logging + tracing helpers
  cli.py          # CLI: baseline / multi-agent / benchmark
tests/            # Unit tests
reports/          # Kết quả benchmark report
```

- `agents/`: trách nhiệm theo role.
- `core/`: contract dữ liệu và cấu hình dùng chung.
- `services/`: tích hợp provider + fallback.
- `graph/`: điều phối vòng chạy agent.
- `evaluation/`: đo lường và xuất báo cáo.
- `observability/`: theo dõi step-by-step.

---

## 4) Cài đặt

### Python version
- Khuyến nghị: **Python 3.11+** (tốt nhất 3.11 hoặc 3.12).

### Tạo virtual environment

```bash
python -m venv .venv
```

Linux/macOS:
```bash
source .venv/bin/activate
```

Windows PowerShell:
```powershell
.\.venv\Scripts\Activate.ps1
```

### Cài dependencies

```bash
pip install -e ".[dev,llm]"
```

### Copy `.env`

Linux/macOS:
```bash
cp .env.example .env
```

Windows PowerShell:
```powershell
copy .env.example .env
```

### Giải thích biến môi trường quan trọng
- `OPENAI_API_KEY`
  - API key OpenAI. Nếu thiếu, hệ thống fallback deterministic mock.
- `OPENAI_MODEL`
  - Model mặc định, ví dụ `gpt-4o-mini`.
- `MAX_ITERATIONS`
  - Số vòng tối đa supervisor được phép route.
- `TIMEOUT_SECONDS`
  - Timeout cho request gọi provider.

Biến hữu ích thêm:
- `TAVILY_API_KEY`: bật tìm kiếm web thật; nếu thiếu sẽ dùng mock search.
- `LANGSMITH_ENABLED`: bật/tắt gửi trace lên LangSmith.

---

## 5) Cách chạy

Thiết lập module path (khuyến nghị):

Linux/macOS:
```bash
export PYTHONPATH=src
```

Windows PowerShell:
```powershell
$env:PYTHONPATH="src"
```

### Chạy test

```bash
make test
```

Nếu máy không có `make`:
```bash
python -m pytest
```

### Chạy single-agent baseline

```bash
python -m multi_agent_research_lab.cli baseline --query "Research GraphRAG state-of-the-art"
```

### Chạy multi-agent

```bash
python -m multi_agent_research_lab.cli multi-agent --query "Research GraphRAG state-of-the-art"
```

### Mô tả output chính
- `final_answer`: câu trả lời cuối.
- `route_history`: lịch sử route qua các agent.
- `trace`: các trace event theo từng step (agent/input/output/latency/error).

---

## 6) Benchmark

### Benchmark dùng để làm gì?
So sánh baseline và multi-agent theo:
- tốc độ,
- chi phí ước tính,
- chất lượng ước tính,
- mức độ citation,
- tỷ lệ lỗi.

### Cách chạy benchmark

```bash
python -m multi_agent_research_lab.cli benchmark
```

### File report nằm ở đâu?
- `reports/benchmark_report.md`

### Giải thích metric
- `latency`: thời gian chạy (giây).
- `cost`: chi phí ước tính USD (dựa trên token usage nếu có).
- `quality`: điểm heuristic 0-10.
- `citation coverage`: tỷ lệ nguồn được tham chiếu trong final answer.
- `failure rate`: tỷ lệ thất bại (theo run, có thể tổng hợp theo nhiều query).

Ví dụ bảng benchmark:

| Run | Latency | Cost | Quality | Citation coverage | Failure rate | Notes |
|---|---:|---:|---:|---:|---:|---|
| baseline:query-x | 8.10s | 0.0000 | 4.0 | 0.00% | 0% | iterations=0 |
| multi-agent:query-x | 24.20s | 0.0000 | 7.2 | 20.00% | 0% | routes=researcher,analyst,writer,done |

---

## 7) So sánh Single-Agent vs Multi-Agent

| Tiêu chí | Single-Agent | Multi-Agent |
|---|---|---|
| Tốc độ | Nhanh hơn | Chậm hơn do nhiều bước |
| Độ đơn giản | Rất đơn giản | Phức tạp hơn do orchestration |
| Khả năng trace/debug | Hạn chế | Tốt hơn, theo từng step |
| Kiểm soát chất lượng | Thấp hơn | Tốt hơn nhờ tách vai trò |
| Cô lập lỗi | Khó hơn | Dễ hơn theo từng agent |

Khi nên dùng multi-agent:
- Bài toán nghiên cứu nhiều bước, cần audit/trace rõ.
- Cần tách trách nhiệm để nâng chất lượng đầu ra.

Khi không nên dùng:
- Query ngắn, đơn giản.
- Yêu cầu latency thấp.
- Hạ tầng tối giản, không cần orchestration.

---

## 8) Trace & Debug

### Trace dùng để làm gì?
- Quan sát được từng bước agent làm gì.
- Nhanh chóng xác định step gây lỗi/chất lượng thấp.
- Giải thích được vì sao final answer xuất hiện như vậy.

### Ví dụ route_history thực tế

```json
["researcher", "analyst", "writer", "done"]
```

### Ví dụ trace JSON rút gọn

```json
[
  {
    "name": "agent_step",
    "payload": {
      "agent": "supervisor",
      "input_summary": "iteration=1 research_notes=False analysis_notes=False final_answer=False errors=0",
      "output_summary": "next_route=researcher",
      "latency_seconds": 0.0001,
      "error": null
    }
  },
  {
    "name": "agent_step",
    "payload": {
      "agent": "researcher",
      "input_summary": "query=Research GraphRAG...",
      "output_summary": "sources=5; notes=...",
      "latency_seconds": 0.4821,
      "error": null
    }
  }
]
```

---

## 9) Failure Modes

Các lỗi phổ biến và cách xử lý:

- Thiếu API key (`OPENAI_API_KEY`)
  - Hiện tượng: fallback mock output hoặc lỗi auth provider.
  - Cách xử lý: điền key đúng trong `.env`.

- LLM fail (timeout/network/provider)
  - Hiện tượng: retry nhiều lần, sau đó fallback.
  - Cách xử lý:
    - kiểm tra mạng,
    - tăng `TIMEOUT_SECONDS`,
    - kiểm tra model name và API key.

- Search fail (Tavily)
  - Hiện tượng: log warning từ search client.
  - Cách xử lý:
    - kiểm tra `TAVILY_API_KEY`,
    - hoặc chấp nhận chạy mock deterministic (vẫn chạy được pipeline).

- Agent loop
  - Hiện tượng: route kéo dài bất thường.
  - Cách xử lý:
    - supervisor đã có `MAX_ITERATIONS` guardrail,
    - giảm/tăng `MAX_ITERATIONS` tùy nhu cầu.

---

## 10) Demo

### Ví dụ query

```bash
python -m multi_agent_research_lab.cli multi-agent --query "Compare vector databases for enterprise RAG deployment in 2026."
```

### Ví dụ output rút gọn

```json
{
  "iteration": 4,
  "route_history": ["researcher", "analyst", "writer", "done"],
  "research_notes": "...",
  "analysis_notes": "...",
  "final_answer": "...",
  "errors": [],
  "estimated_cost_usd": 0.0
}
```

---

## 11) Deliverables (nộp lab)

Checklist nộp bài:
- Repo GitHub
- `reports/benchmark_report.md`
- Trace minh họa (JSON output hoặc screenshot)
- Mô tả failure mode + cách khắc phục

Gợi ý trình bày:
- nêu rõ trade-off latency vs quality giữa single và multi-agent,
- giải thích vì sao chọn multi-agent cho từng loại query.

---

## Lệnh nhanh

```bash
# Lint
make lint

# Type check
make typecheck

# Test
make test

# Baseline
python -m multi_agent_research_lab.cli baseline --query "..."

# Multi-agent
python -m multi_agent_research_lab.cli multi-agent --query "..."

# Benchmark
python -m multi_agent_research_lab.cli benchmark
```

---

## 12) Luồng chạy Multi-Agent: Agent nào chạy khi nào và vì sao?

Dưới đây là luồng thực thi đúng với code hiện tại trong `SupervisorAgent` và `MultiAgentWorkflow`.

### Tổng quan vòng lặp
- Workflow luôn bắt đầu bằng `Supervisor`.
- `Supervisor` chọn route tiếp theo: `researcher`, `analyst`, `writer`, hoặc `done`.
- Sau khi worker chạy xong, workflow quay lại `Supervisor`.
- Lặp lại đến khi route = `done` hoặc đạt giới hạn vòng lặp.

### Rule routing chi tiết (theo thứ tự ưu tiên)
1. Nếu `len(state.errors) >= 4`:
   - Nếu đã có `analysis_notes` nhưng chưa có `final_answer` -> route `writer` (cố gắng kết thúc).
   - Ngược lại -> route `done` (dừng để an toàn).
2. Nếu `state.iteration >= MAX_ITERATIONS` -> route `done`.
3. Nếu chưa có `research_notes` -> route `researcher`.
4. Nếu đã có `research_notes` nhưng chưa có `analysis_notes` -> route `analyst`.
5. Nếu đã có `analysis_notes` nhưng chưa có `final_answer` -> route `writer`.
6. Nếu đã có `final_answer` -> route `done`.

### Từng agent chạy khi nào và vì sao
- **Supervisor**
  - Chạy ở đầu mỗi vòng.
  - Vì sao: cần một điểm trung tâm để quyết định bước tiếp theo và chặn loop vô hạn.

- **Researcher**
  - Chạy khi state chưa có `research_notes`.
  - Vì sao: pipeline cần dữ liệu nền (`sources` + notes) trước khi phân tích.
  - Việc làm: gọi `SearchClient` lấy `sources`, gọi `LLMClient` tạo `research_notes`.

- **Analyst**
  - Chạy khi đã có `research_notes` nhưng chưa có `analysis_notes`.
  - Vì sao: cần biến notes thành insight có cấu trúc (claims, evidence, gaps, viewpoints).

- **Writer**
  - Chạy khi đã có `analysis_notes` nhưng chưa có `final_answer`.
  - Vì sao: cần tổng hợp thành câu trả lời cuối cho user, có tham chiếu nguồn.

- **Done**
  - Chạy khi đã có `final_answer`, hoặc vượt giới hạn iteration, hoặc lỗi tích lũy quá mức an toàn.
  - Vì sao: đảm bảo workflow kết thúc có kiểm soát.

### Ví dụ route_history thường gặp
```json
["researcher", "analyst", "writer", "done"]
```

### Vì sao thiết kế này hợp lý
- Tách trách nhiệm rõ ràng giữa tìm nguồn / phân tích / viết.
- Dễ debug vì mỗi bước đều có `trace`.
- Có guardrails (`MAX_ITERATIONS`, error threshold) để tránh chạy vô hạn.
