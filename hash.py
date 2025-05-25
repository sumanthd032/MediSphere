from flask_bcrypt import Bcrypt
bcrypt = Bcrypt()
password = 'admin123'  # Replace with your desired password
hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
print(hashed_password)