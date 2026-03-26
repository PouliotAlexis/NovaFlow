import jwt
from datetime import datetime, timedelta

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, "change-this-in-production", algorithm="HS256")
    return encoded_jwt

if __name__ == "__main__":
    token = create_access_token(data={"sub": "alexharpou@gmail.com"}, expires_delta=timedelta(hours=1))
    print(token)
