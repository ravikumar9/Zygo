from users.models import User
from payments.models import Wallet

u = User.objects.filter(username='walletuser').first()
print(f'User exists: {u is not None}')

if u:
    w = Wallet.objects.filter(user=u).first()
    if w:
        print(f'Wallet balance: {w.balance}')
        if w.balance < 10000:
            w.balance = 50000
            w.save()
            print(f'Wallet topped up to: {w.balance}')
    else:
        print('User has no wallet - creating one')
        w = Wallet.objects.create(user=u, balance=50000)
        print(f'Wallet created with balance: {w.balance}')
else:
    print('Creating walletuser')
    u = User.objects.create_user(username='walletuser', password='test123', email='wallet@test.com')
    w = Wallet.objects.create(user=u, balance=50000)
    print(f'User and wallet created - balance: {w.balance}')

