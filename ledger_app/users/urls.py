from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AccountViewSet, BudgetViewSet, CalculatorView, LoginView, SignupView, TransactionSummaryView, TransactionViewSet, UserViewSet, send_email

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'accounts', AccountViewSet, basename='account')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'budgets', BudgetViewSet, basename='budget')

urlpatterns = router.urls + [
    path("auth/signup/", SignupView.as_view(), name="signup"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("admin/transactions/summary/", TransactionSummaryView.as_view(), name="transaction-summary"),
    path("calculator/add/", CalculatorView.as_view(), name="calculator-add"),
    path("test_send_email/", send_email)
]
