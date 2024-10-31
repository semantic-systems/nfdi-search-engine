# from typing import Optional
# from werkzeug.security import generate_password_hash, check_password_hash
# from dataclasses import dataclass, fields, field
# from flask_login import UserMixin
# # ...
# @dataclass
# class User(UserMixin):
#     id: int = 0
#     usename: str = ""
#     email: str = ""
#     password_hash: str = ""

#     def __str__(self):
#         return '<User {}>'.format(self.username)

#     def __repr__(self):
#         return '<User {}>'.format(self.username)

#     def set_password(self, password):
#         self.password_hash = generate_password_hash(password)

#     def check_password(self, password):
#         return check_password_hash(self.password_hash, password)

# @login.user_loader
# def load_user(id):
#     # return 
#     return "Rana Abdullah"