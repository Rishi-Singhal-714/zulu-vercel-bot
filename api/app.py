import json

def handler(request, response):
    """
    Vercel-compatible Python function.
    Responds with 'hi' when the incoming message is 'hi'.
    """

    try:
        if request.method == "GET":
            # Simple health check
            response.status_code = 200
            response.body = json.dumps({"status": "ok", "message": "Zulu Club bot running on Vercel!"})
            return response

        if request.method == "POST":
            try:
                data = request.json()
            except Exception:
                response.status_code = 400
                response.body = json.dumps({"error": "Invalid JSON"})
                return response

            message = data.get("message", "").strip().lower()

            if message == "hi":
                reply = "hi 👋"
            else:
                reply = "Hello! Please say 'hi' to start."

            response.status_code = 200
            response.body = json.dumps({"reply": reply})
            return response

        response.status_code = 405
        response.body = json.dumps({"error": "Method not allowed"})
        return response

    except Exception as e:
        response.status_code = 500
        response.body = json.dumps({"error": str(e)})
        return response
