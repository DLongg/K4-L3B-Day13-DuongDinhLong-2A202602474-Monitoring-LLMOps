# Báo cáo cá nhân — K4-L3B Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Chỉ cần 3 output text và 5 ảnh runtime; dùng đường dẫn tương đối, ví dụ `evidence/03-incident-trace.png`.

## 1. Thông tin học viên

- **Họ và tên:** Dương Đình Long
- **MSSV:** 2A202602474
- **Lớp:** K4-L3B
- **Repository URL:** https://github.com/DLongg/K4-L3B-Day13-DuongDinhLong-2A202602474-Monitoring-LLMOps
- **Commit SHA cuối:** `193c7d75820cad68eba03cdf00fae7584be7ca8e`
- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1`
- **Tên project Langfuse cá nhân:** `day13-k4-l3b-2A202602474`

## 2. Evidence index

Giữ đúng ba output text và năm ảnh dưới đây. Không tách thêm ảnh; nếu cần giải thích, ghi bằng chữ trong các mục sau.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/pytest.txt` |
| Log validator | `evidence/log-validator.txt` |
| Dashboard validator | `evidence/dashboard-validator.txt` |
| Structured log + incident log | `evidence/01-incident-log.png` |
| Trace list | `evidence/02-trace-list.png` |
| Trace waterfall + metadata + incident trace | `evidence/03-incident-trace.png` |
| Prompt versions + promote/rollback | `evidence/04-prompt-versioning.png` |
| Dashboard + incident metric | `evidence/05-dashboard-incident.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100 | 100/100 | Baseline thiếu correlation_id và enrichment fields; Sau CP1 đã đạt tối đa |
| `validate_dashboard.py` | 6/6 panel | 6/6 panel | Hợp lệ theo schema và contract |
| `pytest` | 22 passed | 25 passed | Đã bổ sung đầy đủ tests cho CCCD, Credit Card, Passport |
| Số traces hợp lệ | 10 traces | 73 traces/observations | Đã tạo đầy đủ trong project Langfuse cá nhân |
| Số PII leak | 0 | 0 | Không rò rỉ PII trong structured log |
| Latency P95 / TTFT P95 | 393ms / 50ms | 9866ms (incident) / 50ms | Thể hiện rõ spike độ trễ trong bài kiểm tra challenge |
| Retrieval success rate | 100% | 100% | Toàn bộ request thành công |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Trong `CorrelationIdMiddleware`, middleware kiểm tra header `x-request-id`. Nếu có thì sử dụng (ví dụ request test với correlation_id tự đặt: `req-long04`), nếu không có thì tự sinh ngẫu nhiên định dạng `req-<8-hex>` bằng `f"req-{uuid.uuid4().hex[:8]}"`. Trước mỗi request gọi `clear_contextvars()` để chống leak context giữa các request, sau đó gọi `bind_contextvars(correlation_id=correlation_id)` và gán `request.state.correlation_id`. Sau khi gọi `call_next(request)`, middleware gán `correlation_id` và thời gian xử lý `duration_ms` vào response headers `x-request-id` và `x-response-time-ms`.
- **Các metadata được ghi vào structured log:** Bao gồm các trường hệ thống bắt buộc (`ts`, `level`, `service`, `event`, `correlation_id`) và các trường enrichment từ context request (`user_id_hash` băm sha256 12 ký tự, `session_id`, `feature`, `model`, `env`). Với event `response_sent`, còn ghi nhận `latency_ms`, `ttft_ms`, `tokens_in`, `tokens_out`, `cost_usd`, `quality_score`, `tool_name`, `tool_success` và `payload` chứa `answer_preview`.
- **Cách bảo đảm PII được scrub trước khi ghi:** Processor `scrub_event` duyệt đệ quy qua các giá trị chuỗi, danh sách, và từ điển, sử dụng các regex pattern trong `PII_PATTERNS` để thay thế thông tin nhạy cảm (email, số điện thoại Việt Nam các định dạng, CCCD 12 số, thẻ thanh toán 16 số, hộ chiếu). `scrub_event` được đăng ký vào pipeline `structlog.configure` đứng ngay TRƯỚC `JsonlFileProcessor` và `JSONRenderer`, đảm bảo mọi dữ liệu nhạy cảm được che (redacted) trước khi render hoặc ghi file xuống đĩa.
- **Cách kiểm chứng kết quả:** Chạy `python scripts/load_test.py` với các câu hỏi chứa dữ liệu nhạy cảm mẫu, sau đó chạy `python scripts/validate_logs.py` kiểm tra toàn bộ file `data/logs.jsonl` đạt 100/100, 0 PII leaks, 27 unique correlation IDs; đồng thời 25/25 unit tests bao gồm toàn bộ tests PII trong `tests/test_pii.py` đều pass.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** Toàn bộ traces đều được đẩy trực tiếp lên project Langfuse cá nhân mang tên `day13-k4-l3b-2A202602474` (xác thực qua API Key cá nhân trong file `.env`). Mọi trace đều mang environment `dev`, tags `["lab", feature, "claude-sonnet-4-5"]` và metadata chứa đúng `correlation_id` khớp với log cục bộ tại `data/logs.jsonl`.
- **Cấu trúc root/retrieval/generation observations:**
  - *Root Trace:* `day13-agent-request` (bọc toàn bộ request).
  - *Agent Observation:* `lab-agent-run` (type `agent`) ghi nhận input, output và metadata tổng quan của agent.
  - *Child Span 1 (Retrieval):* `@observe(name="retrieval", as_type="retriever")` đo thời gian truy xuất tài liệu vector/RAG corpus.
  - *Child Span 2 (Generation):* `@observe(name="generation", as_type="generation")` đo thời gian gọi LLM sinh text, gắn liên kết tới prompt template, đo lường chi tiết usage (`input_tokens`, `output_tokens`) và `cost_usd`.
- **Cách nối trace với log:** Sử dụng `correlation_id`. Khi middleware nhận/sinh correlation ID (ví dụ `req-a363e36a`), ID này vừa được bind vào contextvars của `structlog` để in vào từng dòng log JSONL, vừa được đưa vào `propagate_attributes(metadata={"correlation_id": correlation_id})` của Langfuse. Nhờ đó, khi gặp một log bất thường, chỉ cần copy `correlation_id` tìm kiếm trên Langfuse là ra ngay trace tương ứng.
- **Prompt name:** `day13-chat`
- **Version/label baseline:** Version 1 (nhãn: `baseline`, template gồm các biến `{{feature}}`, `{{docs}}`, `{{message}}`).
- **Version/label candidate:** Version 2 (nhãn: `candidate`, bổ sung yêu cầu trả lời ngắn gọn trong 3 bullet points).
- **Trace ID của mỗi version:**
  - *Trace version 1 (baseline/production):* `2e49778499d1c8c6c65c00073d70ee97` (chạy với version 1).
  - *Trace version 2 (production v2):* `f00b3a266f95b6e1ac88a6d68b6ff9a9` (chạy với prompt v2, hiển thị rõ `Prompt: day13-chat - v2`).
- **Cách promote và rollback `production`:**
  - *Promote:* Trên giao diện Langfuse Prompt Management, chọn prompt `day13-chat`, gán label `production` cho Version 2. Ứng dụng production tải prompt theo nhãn `production` sẽ chuyển sang thực thi Version 2.
  - *Rollback:* Khi Version 2 gặp sự cố hoặc cần quay lại bản ổn định, gỡ label `production` ở Version 2 và gán lại cho Version 1. Quá trình rollback diễn ra ngay lập tức trên Langfuse Cloud mà không cần sửa code hay rebuild/redeploy image của hệ thống.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** Dựng đủ 6 panel chuẩn từ nguồn `data/logs.jsonl` theo `config/dashboard.yaml`: (1) Latency: đo P50, P95, P99 và TTFT P95 với threshold P95 <= 3000ms; (2) Traffic: đo request rate theo phút với threshold >= 1 req/min; (3) Errors: đo error_rate_pct và tool_success_rate_pct (retrieval) với threshold error rate <= 2%; (4) Cost: đo chi phí USD theo phút và tổng chi phí với threshold total <= 2.5 USD; (5) Tokens: đo tổng tokens_in và tokens_out với threshold sum <= 50,000 tokens; (6) Quality: đo chất lượng trung bình với threshold mean >= 0.75.
- **SLO và lý do chọn:** Chọn primary SLO `fast_successful_requests` với mục tiêu 99.5% request thành công và có `latency_ms <= 3000ms` trong cửa sổ 28 ngày. Lý do chọn: Người dùng chatbot LLM cần trải nghiệm mượt mà, phản hồi dưới 3 giây và không bị lỗi gián đoạn. Dữ liệu baseline thực tế cho thấy latency P95 bình thường khoảng ~395ms và retrieval success 100%, do đó ngưỡng 3000ms bảo đảm trải nghiệm tốt mà vẫn có biên độ an toàn khi traffic biến động.
- **Cách tính error budget:** Với target SLO 99.5%, error budget là 0.5% (100% - 99.5%). Trong cửa sổ 28 ngày, nếu hệ thống nhận 10,000 request thì error budget cho phép tối đa 50 request bị lỗi (HTTP 500) hoặc có latency vượt quá 3000ms trước khi vi phạm cam kết dịch vụ.
- **Ba alert và runbook tương ứng:**
  - `HighLatencyP95` (warning, 5m): kích hoạt khi `p95(latency_ms) > 3000ms` duy trì 5 phút. Runbook tại `docs/alerts.md#alert-1`.
  - `HighErrorRate` (critical, 5m): kích hoạt khi `error_rate_pct > 2%` duy trì 5 phút. Runbook tại `docs/alerts.md#alert-2`.
  - `LowRetrievalSuccess` (warning, 5m): kích hoạt khi `retrieval_success_rate_pct < 90%` duy trì 5 phút. Runbook tại `docs/alerts.md#alert-3`.

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1`
- **Khoảng thời gian điều tra:** 2026-09-30 04:35:47Z – 04:36:12Z (11:35 – 11:36 giờ địa phương).
- **Triệu chứng từ metrics:** Trên Dashboard 6 panel (Ảnh 05), panel Latency ghi nhận tail latency P95 tăng vọt lên **9866.0 ms**, vượt rất xa ngưỡng cảnh báo SLO Guardrail (3000 ms). Đồng thời traffic tăng vọt lên 4.0 req/min do concurrency test.
- **Log line và correlation ID liên quan:** Tại dòng log trong `data/logs.jsonl` (Ảnh 01), event `response_sent` lúc `2026-09-30T04:35:50.476825Z` có `correlation_id: req-a363e36a`, `session_id: k4-l3b-challenge-s02`, `latency_ms: 2653` (vượt ngưỡng 2000ms), `feature: monitoring`.
- **Trace ID và span gây ảnh hưởng:** Mở trace trên Langfuse (Ảnh 03) có cùng `correlation_id: req-a363e36a`, Trace ID là **`2e49778499d1c8c6c65c00073d70ee97`**. Waterfall span tree chỉ ra rõ ràng span **`retrieval`** kéo dài bất thường tới **`2.50s`** (chiếm tới 94% tổng thời gian thực thi 2.66s của request), trong khi span `generation` chỉ mất 0.15s.
- **Root cause:** Sự cố `rag_slow` được kích hoạt khiến hàm `retrieve()` bị trễ (mô phỏng nghẽn mạng hoặc database vector store quá tải với delay 2.5s), dẫn đến toàn bộ thời gian phản hồi của agent bị chậm nghiêm trọng, gây ra vi phạm SLO latency.
- **Fix action:** Thực hiện tắt sự cố bằng cách gọi API `/incidents/rag_slow/disable` qua lệnh `python scripts/inject_incident.py --disable`, khôi phục vector store/retrieval service về hoạt động bình thường (< 50ms).
- **Preventive measure:** Áp dụng timeout nghiêm ngặt cho span retrieval (ví dụ: timeout = 2000ms); nếu retrieval quá thời gian thì tự động fallback về văn bản mặc định (fallback documents) và trả lời người dùng thay vì treo request; đồng thời thiết lập alert `HighLatencyP95` để đội trực vận hành phát hiện ngay khi P95 vượt 3000ms trong 5 phút.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** Quyết định tích hợp `CorrelationIdMiddleware` ở tầng ngoài cùng của FastAPI và truyền `correlation_id` đồng nhất vào cả `structlog` (local file JSONL) lẫn `propagate_attributes` của Langfuse (distributed tracing). Quyết định này giúp kết nối liền mạch luồng observability từ Metrics (Dashboard cảnh báo) → Logs (tìm correlation_id) → Traces (phân tích span waterfall để tìm root cause), giải quyết bài toán phân mảnh dữ liệu giám sát.
- **Một lỗi/blocker đã gặp:** Khi promote Version 2 trên web Langfuse, do SDK Langfuse có cơ chế caching prompt (`cache_ttl_seconds=60`) và tiến trình server uvicorn đang chạy liên tục, các request chat ngay sau đó vẫn nhận prompt Version 1 từ bộ nhớ đệm.
- **Cách tìm nguyên nhân và xử lý:** Kiểm tra log và mã nguồn `prompt_management.py`, phát hiện tham số `cache_ttl_seconds=60`. Đã xử lý bằng cách reload tiến trình uvicorn để xóa sạch cache của tiến trình cũ, nhờ đó server lập tức fetch prompt Version 2 từ Langfuse Cloud về.
- **Cách hiểu luồng Metrics → Logs → Traces:** 
  1. *Metrics* là tầng phát hiện đầu tiên (detection) với chi phí thấp, giúp nhận diện hệ thống đang có vấn đề gì (ví dụ: Latency P95 spike vượt ngưỡng 3000ms).
  2. *Logs* là tầng khoanh vùng (isolation) giúp tìm ra chính xác request nào, người dùng nào, session nào đang bị lỗi hoặc chạy chậm trong khoảng thời gian đó, thông qua `correlation_id`.
  3. *Traces* là tầng chẩn đoán chuyên sâu (diagnosis) giúp đi sâu vào bên trong từng span/observation của request để xác định chính xác thành phần gây lỗi/chậm (ví dụ: span `retrieval` bị nghẽn 2.5s thay vì do LLM).
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:**
  - *Prompt Versioning & Rollback:* Giúp quản trị prompt như code nhưng có thể promote/rollback độc lập mà không cần redeploy toàn bộ ứng dụng, giảm thiểu rủi ro khi thay đổi system prompt.
  - *Token & Cost:* Cho phép theo dõi chi phí theo thời gian thực, kịp thời phát hiện prompt bị rò rỉ token hoặc tấn công sinh text quá dài (cost spike).
  - *SLO & Error Budget:* Cung cấp thước đo định lượng khách quan về chất lượng dịch vụ cam kết với người dùng, đồng thời làm căn cứ để đưa ra quyết định đóng/mở tính năng hoặc dừng deploy khi error budget cạn kiệt.
- **Điều quan trọng nhất đã học:** Hiểu và áp dụng thành thạo nguyên tắc Observability 3 trụ cột (Metrics - Logs - Traces) trong một ứng dụng AI/LLMOps thực tế, kết hợp cơ chế che giấu thông tin nhạy cảm (PII Redaction) ngay từ tầng thu thập log để đảm bảo an toàn bảo mật dữ liệu.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:** Các metric hiện tại chủ yếu đọc từ file `logs.jsonl` cục bộ; trên môi trường production quy mô lớn cần chuyển sang xuất metric dạng Prometheus/OpenTelemetry Collector và tập trung log về Elasticsearch/Loki.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Có đúng 3 file text và 5 ảnh runtime theo hướng dẫn.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [ ] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
