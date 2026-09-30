# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert mẫu để tham khảo

Ví dụ dưới đây minh họa mức độ cụ thể cần có. Học viên không cần copy nguyên, nhưng ba alert trong bài nộp nên rõ ràng tương tự: điều kiện là gì, kéo dài bao lâu, ảnh hưởng tới user ra sao và người trực cần kiểm tra gì trước.

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: latency P95 của `response_sent.latency_ms`
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` trong 5 phút
- Ảnh hưởng tới người dùng: người dùng phải chờ lâu hơn trước khi nhận câu trả lời
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard latency để xác nhận P95/P99 và khoảng thời gian tăng.
  2. Lọc `data/logs.jsonl` trong khoảng đó, lấy một `correlation_id` có `latency_ms` cao.
  3. Mở trace cùng `correlation_id` trên Langfuse, so sánh các span chính để xác định bước nào bất thường.
- Mitigation tạm thời: dựa trên evidence thực tế để rollback prompt, khôi phục cấu hình liên quan, tắt practice scenario hoặc giảm tải khi demo.
- Owner: `student-<MSSV>`

## Alert 1

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: latency P95 của `response_sent.latency_ms`
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` trong 5 phút
- Ảnh hưởng tới người dùng: Người dùng phải chờ lâu hơn trước khi nhận câu trả lời từ chatbot/API.
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard latency để xác nhận P95/P99 và khoảng thời gian latency bắt đầu tăng vọt.
  2. Lọc `data/logs.jsonl` trong khoảng đó, lấy một `correlation_id` có `latency_ms` cao bất thường.
  3. Mở trace cùng `correlation_id` trên Langfuse, so sánh span `retrieval` và `generation` để xác định bước nào gây chậm trễ (ví dụ: vector store timeout hay LLM chậm).
- Mitigation tạm thời: Dựa trên evidence để rollback prompt version nếu vừa cập nhật, giảm tải/concurrency, hoặc khởi động lại dịch vụ nếu tài nguyên bị nghẽn.
- Owner: `student-2A202602474`

## Alert 2

- Tên: `HighErrorRate`
- Severity: `critical`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: Error rate percentage (`count(request_failed) / count(request_received) * 100`)
- Điều kiện và thời gian duy trì: `error_rate_pct > 2%` trong 5 phút
- Ảnh hưởng tới người dùng: Request của người dùng bị gián đoạn, nhận lỗi HTTP 500 hoặc không có câu trả lời.
- Ba bước kiểm tra đầu tiên:
  1. Mở panel Errors trên dashboard để xác nhận tỷ lệ lỗi và xem `error_type` phổ biến nhất (ví dụ: RuntimeError, Timeout).
  2. Lọc `data/logs.jsonl` tìm các log `request_failed` gần nhất, lấy `correlation_id` và xem thông báo `detail` trong payload.
  3. Mở trace tương ứng trên Langfuse để kiểm tra span nào bị gán status ERROR và stack trace chi tiết.
- Mitigation tạm thời: Khôi phục cấu hình hoặc tắt scenario incident giả lập (`/incidents/{name}/disable`), restart API container nếu crash loop.
- Owner: `student-2A202602474`

## Alert 3

- Tên: `LowRetrievalSuccess`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: Retrieval tool success rate (`count(tool_success == true) / count(tool_success != null) * 100`)
- Điều kiện và thời gian duy trì: `retrieval_success_rate_pct < 90%` trong 5 phút
- Ảnh hưởng tới người dùng: Hệ thống RAG không lấy được tài liệu phù hợp, dẫn đến câu trả lời chất lượng kém hoặc fallback rỗng.
- Ba bước kiểm tra đầu tiên:
  1. Mở panel Errors trên dashboard để xem biểu đồ `tool_success_rate_pct` và kiểm tra thời điểm giảm dưới ngưỡng 90%.
  2. Lọc `data/logs.jsonl` tìm các log có `tool_success: false` hoặc `tool_name: "retrieval"` kèm lỗi.
  3. Mở trace trên Langfuse, kiểm tra observation `retrieval` để xem thời gian phản hồi của retrieval và lỗi trả về từ vector database / corpus.
- Mitigation tạm thời: Kiểm tra kết nối tới cơ sở dữ liệu vector/corpus, chuyển sang chế độ retrieval fallback hoặc phục hồi service mock nếu vector store bị gián đoạn.
- Owner: `student-2A202602474`

