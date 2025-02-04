import os
from flask import Flask, render_template, request, send_from_directory
import expense_processor

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        if "file" not in request.files:
            return render_template("index.html", error_message="No file uploaded")
            
        file = request.files["file"]
        if file.filename == "":
            return render_template("index.html", error_message="No file selected")

        try:
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            file.save(file_path)
            stats, graph_filenames = expense_processor.analyze_transactions(file_path)
            
            if stats.get("error"):
                return render_template("index.html", error_message=stats["error"])
                
            return render_template("index.html", 
                                analysis_result=stats,
                                graph_filenames=graph_filenames,
                                error_message=None)
                                
        except Exception as e:
            return render_template("index.html", 
                                error_message=f"System Error: {str(e)}")

    return render_template("index.html", 
                         analysis_result=None, 
                         graph_filenames=None,
                         error_message=None)

@app.route("/graphs/<filename>")
def get_graph(filename):
    return send_from_directory("static/graphs", filename)

if __name__ == "__main__":
    app.run(debug=True)