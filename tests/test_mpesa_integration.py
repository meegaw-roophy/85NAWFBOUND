from payments.mpesa_integration import initiate_stk_push


class TestInitiateStkPush:
    def test_returns_queued(self):
        result = initiate_stk_push("254712345678", 250.0)
        assert result["status"] == "queued"
        assert result["phone"] == "254712345678"
        assert result["amount"] == 250.0

    def test_zero_amount(self):
        result = initiate_stk_push("254712345678", 0)
        assert result["status"] == "queued"
        assert result["amount"] == 0

    def test_negative_amount(self):
        result = initiate_stk_push("254712345678", -100)
        assert result["status"] == "queued"
        assert result["amount"] == -100
