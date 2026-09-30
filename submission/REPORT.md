# Báo cáo cá nhân — K4-L3B Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Chỉ cần 3 output text và 5 ảnh runtime; dùng đường dẫn tương đối, ví dụ `evidence/03-incident-trace.png`.

## 1. Thông tin học viên

- **Họ và tên:** Dương Đình Long
- **MSSV:** 2A202602474
- **Lớp:** K4-L3B
- **Repository URL:** https://github.com/DLongg/K4-L3B-Day13-DuongDinhLong-2A202602474-Monitoring-LLMOps
- **Commit SHA cuối:**
- **Challenge ID:**
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
| Số traces hợp lệ | 10 traces | 10 traces | Đã tạo trong project Langfuse cá nhân |
| Số PII leak | 0 | 0 | Không rò rỉ PII trong structured log |
| Latency P95 / TTFT P95 | 393ms / 50ms | 395ms / 50ms | Baseline và runtime ổn định |
| Retrieval success rate | 100% | 100% | Toàn bộ 10/10 request baseline thành công |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Trong `CorrelationIdMiddleware`, middleware kiểm tra header `x-request-id`. Nếu có thì sử dụng (ví dụ request test với correlation_id tự đặt: `req-long04`), nếu không có thì tự sinh ngẫu nhiên định dạng `req-<8-hex>` bằng `f"req-{uuid.uuid4().hex[:8]}"`. Trước mỗi request gọi `clear_contextvars()` để chống leak context giữa các request, sau đó gọi `bind_contextvars(correlation_id=correlation_id)` và gán `request.state.correlation_id`. Sau khi gọi `call_next(request)`, middleware gán `correlation_id` và thời gian xử lý `duration_ms` vào response headers `x-request-id` và `x-response-time-ms`.
- **Các metadata được ghi vào structured log:** Bao gồm các trường hệ thống bắt buộc (`ts`, `level`, `service`, `event`, `correlation_id`) và các trường enrichment từ context request (`user_id_hash` băm sha256 12 ký tự, `session_id`, `feature`, `model`, `env`). Với event `response_sent`, còn ghi nhận `latency_ms`, `ttft_ms`, `tokens_in`, `tokens_out`, `cost_usd`, `quality_score`, `tool_name`, `tool_success` và `payload` chứa `answer_preview`.
- **Cách bảo đảm PII được scrub trước khi ghi:** Processor `scrub_event` duyệt đệ quy qua các giá trị chuỗi, danh sách, và từ điển, sử dụng các regex pattern trong `PII_PATTERNS` để thay thế thông tin nhạy cảm (email, số điện thoại Việt Nam các định dạng, CCCD 12 số, thẻ thanh toán 16 số, hộ chiếu). `scrub_event` được đăng ký vào pipeline `structlog.configure` đứng ngay TRƯỚC `JsonlFileProcessor` và `JSONRenderer`, đảm bảo mọi dữ liệu nhạy cảm được che (redacted) trước khi render hoặc ghi file xuống đĩa.
- **Cách kiểm chứng kết quả:** Chạy `python scripts/load_test.py` với các câu hỏi chứa dữ liệu nhạy cảm mẫu, sau đó chạy `python scripts/validate_logs.py` kiểm tra toàn bộ file `data/logs.jsonl` đạt 100/100, 0 PII leaks, 10 unique correlation IDs; đồng thời 25/25 unit tests bao gồm toàn bộ tests PII trong `tests/test_pii.py` đều pass.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:**
- **Cấu trúc root/retrieval/generation observations:**
- **Cách nối trace với log:**
- **Prompt name:**
- **Version/label baseline:**
- **Version/label candidate:**
- **Trace ID của mỗi version:**
- **Cách promote và rollback `production`:**

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** Dựng đủ 6 panel chuẩn từ nguồn `data/logs.jsonl` theo [config/dashboard.yaml](file:///d:/AI_20K/Lab13/K4-L3B-Day13-DuongDinhLong-2A202602474-Monitoring-LLMOps/config/dashboard.yaml): (1) Latency: đo P50, P95, P99 và TTFT P95 với threshold P95 <= 3000ms; (2) Traffic: đo request rate theo phút với threshold >= 1 req/min; (3) Errors: đo error_rate_pct và tool_success_rate_pct (retrieval) với threshold error rate <= 2%; (4) Cost: đo chi phí USD theo phút và tổng chi phí với threshold total <= 2.5 USD; (5) Tokens: đo tổng tokens_in và tokens_out với threshold sum <= 50,000 tokens; (6) Quality: đo chất lượng trung bình với threshold mean >= 0.75.
- **SLO và lý do chọn:** Chọn primary SLO `fast_successful_requests` với mục tiêu 99.5% request thành công và có `latency_ms <= 3000ms` trong cửa sổ 28 ngày. Lý do chọn: Người dùng chatbot LLM cần trải nghiệm mượt mà, phản hồi dưới 3 giây và không bị lỗi gián đoạn. Dữ liệu baseline thực tế cho thấy latency P95 khoảng 395ms và retrieval success 100%, do đó ngưỡng 3000ms bảo đảm trải nghiệm tốt mà vẫn có biên độ an toàn khi traffic biến động.
- **Cách tính error budget:** Với target SLO 99.5%, error budget là 0.5% (100% - 99.5%). Trong cửa sổ 28 ngày, nếu hệ thống nhận 10,000 request thì error budget cho phép tối đa 50 request bị lỗi (HTTP 500) hoặc có latency vượt quá 3000ms trước khi vi phạm cam kết dịch vụ.
- **Ba alert và runbook tương ứng:**
  - `HighLatencyP95` (warning, 5m): kích hoạt khi `p95(latency_ms) > 3000ms` duy trì 5 phút. Runbook tại `docs/alerts.md#alert-1`.
  - `HighErrorRate` (critical, 5m): kích hoạt khi `error_rate_pct > 2%` duy trì 5 phút. Runbook tại `docs/alerts.md#alert-2`.
  - `LowRetrievalSuccess` (warning, 5m): kích hoạt khi `retrieval_success_rate_pct < 90%` duy trì 5 phút. Runbook tại `docs/alerts.md#alert-3`.


## 7. Điều tra challenge

- **Challenge ID:**
- **Khoảng thời gian điều tra:**
- **Triệu chứng từ metrics:**
- **Log line và correlation ID liên quan:**
- **Trace ID và span gây ảnh hưởng:**
- **Root cause:**
- **Fix action:**
- **Preventive measure:**

> Gợi ý cách viết ngắn, không thay cho evidence thực tế: "Metric cho thấy `[latency/error/cost/quality]` bất thường trong `[khoảng thời gian]`. Log line `[event]` có `correlation_id=[...]` đại diện cho request bị ảnh hưởng. Trace cùng `correlation_id` cho thấy span `[retrieval/generation/prompt/tool]` có dấu hiệu `[chậm/lỗi/token tăng]`. Root cause là `[nguyên nhân suy ra từ evidence]`. Fix action là `[hành động khôi phục]`; preventive measure là `[alert/runbook/test/guardrail để ngăn tái diễn]`."

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:**
- **Một lỗi/blocker đã gặp:**
- **Cách tìm nguyên nhân và xử lý:**
- **Cách hiểu luồng Metrics → Logs → Traces:**
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:**
- **Điều quan trọng nhất đã học:**
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:**

## 9. Checklist trước khi nộp

- [ ] Kết quả và evidence thuộc commit SHA cuối.
- [ ] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [ ] Có đúng 3 file text và 5 ảnh runtime theo hướng dẫn.
- [ ] Incident evidence nối đúng metric → log → trace.
- [ ] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [ ] Repository chạy lại được theo README.
- [ ] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [ ] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
