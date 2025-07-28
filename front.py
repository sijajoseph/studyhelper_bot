

# -----------------------------------------
# ✅ FRONTEND: Gradio Client (gradio_ui.py)
# -----------------------------------------
from logging import log
from pydoc_data import topics
import gradio as gr
from gradio_pdf import PDF
import requests
from typing import List, Tuple, Dict, Any




API_BASE = "http://localhost:8080"  # Make sure FastAPI backend runs here

def upload_pdfs(pdf_files: List[Any]) :
    files = []
    for pdf in pdf_files:
        with open(pdf.name, "rb") as f:
            files.append(("files", (pdf.name, f.read(), "application/pdf")))

    response = requests.post(f"{API_BASE}/upload", files=files)

    if not response.ok:
        return "❌ Upload failed.", *[gr.update(visible=False) for _ in range(20)], {}

    # Get topics from response
    topics = response.json().get("topics", {})

    # Log for debugging
    
    print(topics)
    # Prepare button updates using simple for loop
    updates= []
    for i in range(20):
        
        if str(i) in topics:
            
            topic_name = topics[str(i)]['topic']
            updates.append(gr.update(value=f"📄 {topic_name}", visible=True))
        else:
            updates.append(gr.update(visible=False))
    
    return "✅ Upload successful!", *updates, topics


def ask_question_gradio(q: str) -> str:
    res = requests.post(f"{API_BASE}/ask", data={"question": q})
    return res.json().get("answer", "Error answering question.")
def summarize():
    return ask_question_gradio("Summarize all the contents  in the pdfs into a big paragraph by mentioning every topic")
    
def fetch_topic_answer(idx: int, topics: Dict[int, Dict[str, str]]) -> str:
    if str(idx) in topics:
        topic = topics[str(idx)]["topic"]
        return ask_question_gradio(f"What is {topic}?")
    return "❌ Topic not found."


def fetch_pdf(idx: int, topics: Dict[int, Dict[str, str]]) :
    if str(idx) in topics or idx in topics:
        filename: str = topics[str(idx)]['file']
        res = requests.get(f"{API_BASE}/pdf/{filename}")
        
        pdf_path= res.json()["path"]
        page_number=int(topics[str(idx)]["page"])
        if res.ok:
            print(f"{pdf_path}#page={page_number}")
            return pdf_path
    return ""

with gr.Blocks(title="📚 Study PDF QA Bot") as demo:
    gr.Markdown("## 📖 Study Assistant\nUpload PDFs, explore topics, and ask questions.")

    topics_state: gr.State = gr.State({})

    with gr.Row():
        pdf_input: gr.File = gr.File(file_types=[".pdf"], file_count="multiple", label="📚 Upload PDFs")
        upload_btn: gr.Button = gr.Button("📥 Upload + Extract Topics")

    upload_status: gr.Textbox = gr.Textbox(label="Status", interactive=False)
    with gr.Row():
        question: gr.Textbox = gr.Textbox(label="Ask a Question")
        answer: gr.Textbox = gr.Textbox(label="Answer", lines=6)
    with gr.Row():
        with gr.Column(scale=2):
            pdf_viewer=PDF(label="📖 PDF Viewer", interactive=True,elem_id="pdf_viewer")
        with gr.Column(scale=1):
            gr.Markdown("### 🧠 Topics")
            topic_buttons: List[gr.Button] = []
            for i in range(20):
                
                btn: gr.Button = gr.Button(visible=False)
                btn.click(fn=fetch_pdf, inputs=[gr.State(i), topics_state], outputs=[pdf_viewer])
                btn.click(fn=fetch_topic_answer, inputs=[gr.State(i), topics_state], outputs=[answer])
                topic_buttons.append(btn)
    with  gr.Row():
        summarize_button=gr.Button("Summarize",visible = True)
        summarize_button.click(
            fn=summarize,
            inputs=[],
            outputs=[answer]
		)
    

    upload_btn.click(
        fn=upload_pdfs,
        inputs=[pdf_input],
        outputs=[upload_status] + topic_buttons + [topics_state]
    )

    question.submit(fn=ask_question_gradio, inputs=[question], outputs=[answer])

if __name__ == "__main__":
    demo.launch()
