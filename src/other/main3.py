from fastapi import FastAPI, Request, Response
import base64

app = FastAPI()

@app.middleware("http")
async def session_timeout_middleware(request: Request, call_next):
    # 1. Revisar si ya tiene la cookie de sesión
    session = request.cookies.get("session_access")
    
    if session == "authorized":
        return await call_next(request)

    # 2. Si no tiene cookie, revisar si está enviando Basic Auth
    auth_header = request.headers.get("Authorization")
    
    if auth_header:
        # Validar usuario:password (admin:secreto123)
        encoded_credentials = auth_header.split(" ")[1]
        decoded = base64.b64decode(encoded_credentials).decode("utf-8")
        
        if decoded == "admin:secreto123":
            response = await call_next(request)
            # 3. SETEAR LA COOKIE POR 1 HORA (3600 seg)
            response.set_cookie(
                key="session_access", 
                value="authorized", 
                max_age=3600,  # <--- AQUÍ DEFINES EL TIEMPO
                httponly=True
            )
            return response

    # 4. Si no hay nada, pedir credenciales
    return Response(
        "Sesión expirada o no autorizada", 
        status_code=401, 
        headers={"WWW-Authenticate": "Basic"}
    )