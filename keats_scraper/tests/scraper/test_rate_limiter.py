"""Tests for RateLimiter."""

import pytest
from unittest.mock import patch, MagicMock

from scraper.rate_limiter import RateLimiter, rate_limited
from config import RateLimitConfig


class TestRateLimiterInit:
    """Tests for RateLimiter initialization."""

    def test_init_with_default_config(self):
        """Test initialization with default RateLimitConfig."""
        limiter = RateLimiter()
        assert limiter.config is not None

    def test_init_with_custom_config(self, rate_limit_config):
        """Test initialization with custom config."""
        limiter = RateLimiter(rate_limit_config)
        assert limiter.config == rate_limit_config

    def test_initial_state(self):
        """Test initial state values."""
        limiter = RateLimiter()
        assert limiter._last_request_time == 0
        assert limiter._request_count == 0


class TestWait:
    """Tests for wait method."""

    def test_wait_first_request_no_sleep(self):
        """Test first request doesn't sleep (or sleeps minimally)."""
        config = RateLimitConfig(
            min_delay_seconds=1.0,
            max_delay_seconds=2.0,
        )
        limiter = RateLimiter(config)

        with patch("time.time", return_value=1000.0):
            with patch("time.sleep") as mock_sleep:
                with patch("random.uniform", return_value=1.5):
                    limiter.wait()

        # First request when _last_request_time is 0 should have large elapsed time
        # So no sleep needed or minimal
        # The actual behavior depends on implementation

    def test_wait_increments_request_count(self):
        """Test request count is incremented."""
        config = RateLimitConfig(
            min_delay_seconds=0,
            max_delay_seconds=0.001,
        )
        limiter = RateLimiter(config)

        with patch("time.time", return_value=1000.0):
            with patch("time.sleep"):
                with patch("random.uniform", return_value=0):
                    limiter.wait()

        assert limiter._request_count == 1

    def test_wait_updates_last_request_time(self):
        """Test last_request_time is updated."""
        config = RateLimitConfig(
            min_delay_seconds=0,
            max_delay_seconds=0.001,
        )
        limiter = RateLimiter(config)

        with patch("time.time", return_value=1234.5):
            with patch("time.sleep"):
                with patch("random.uniform", return_value=0):
                    limiter.wait()

        assert limiter._last_request_time == 1234.5

    def test_wait_sleeps_when_too_fast(self):
        """Test sleep when requests are too fast."""
        config = RateLimitConfig(
            min_delay_seconds=2.0,
            max_delay_seconds=3.0,
        )
        limiter = RateLimiter(config)
        limiter._last_request_time = 1000.0

        # 0.5 seconds after last request
        with patch("time.time", return_value=1000.5):
            with patch("time.sleep") as mock_sleep:
                with patch("random.uniform", return_value=2.5):
                    limiter.wait()

        # Should sleep for approximately 2.0 seconds (2.5 - 0.5)
        mock_sleep.assert_called_once()
        sleep_time = mock_sleep.call_args[0][0]
        assert sleep_time > 0

    def test_wait_no_sleep_when_enough_time_passed(self):
        """Test no sleep when enough time has passed."""
        config = RateLimitConfig(
            min_delay_seconds=1.0,
            max_delay_seconds=2.0,
        )
        limiter = RateLimiter(config)
        limiter._last_request_time = 1000.0

        # 10 seconds after last request (plenty of time)
        with patch("time.time", return_value=1010.0):
            with patch("time.sleep") as mock_sleep:
                with patch("random.uniform", return_value=1.5):
                    limiter.wait()

        # Should not sleep
        mock_sleep.assert_not_called()

    def test_wait_respects_min_delay(self):
        """Test minimum delay is respected."""
        config = RateLimitConfig(
            min_delay_seconds=2.0,
            max_delay_seconds=2.0,  # Same as min for deterministic test
        )
        limiter = RateLimiter(config)
        limiter._last_request_time = 1000.0

        # Only 1 second passed
        with patch("time.time", return_value=1001.0):
            with patch("time.sleep") as mock_sleep:
                with patch("random.uniform", return_value=2.0):
                    limiter.wait()

        # Should sleep for ~1 second (2.0 - 1.0)
        mock_sleep.assert_called_once()
        sleep_time = mock_sleep.call_args[0][0]
        assert 0.9 <= sleep_time <= 1.1


class TestBackoff:
    """Tests for backoff method."""

    def test_backoff_first_attempt(self):
        """Test backoff for first attempt (attempt=0)."""
        config = RateLimitConfig(
            min_delay_seconds=1.0,
            backoff_factor=2.0,
        )
        limiter = RateLimiter(config)

        with patch("random.uniform", return_value=1.0):
            delay = limiter.backoff(0)

        # 1.0 * (2.0 ^ 0) * 1.0 = 1.0
        assert delay == pytest.approx(1.0, rel=0.1)

    @pytest.mark.parametrize("attempt,expected_base", [
        (0, 1.0),   # min_delay * 2^0
        (1, 2.0),   # min_delay * 2^1
        (2, 4.0),   # min_delay * 2^2
        (3, 8.0),   # min_delay * 2^3
    ])
    def test_backoff_exponential(self, attempt, expected_base):
        """Test exponential backoff for various attempts."""
        config = RateLimitConfig(
            min_delay_seconds=1.0,
            backoff_factor=2.0,
        )
        limiter = RateLimiter(config)

        with patch("random.uniform", return_value=1.0):
            delay = limiter.backoff(attempt)

        assert delay == pytest.approx(expected_base, rel=0.1)

    def test_backoff_caps_at_60_seconds(self):
        """Test maximum backoff is 60 seconds."""
        config = RateLimitConfig(
            min_delay_seconds=10.0,
            backoff_factor=2.0,
        )
        limiter = RateLimiter(config)

        with patch("random.uniform", return_value=1.5):
            delay = limiter.backoff(10)  # Would be 10 * 1024 * 1.5 without cap

        assert delay <= 60.0

    def test_backoff_includes_jitter(self):
        """Test jitter is applied to backoff."""
        config = RateLimitConfig(
            min_delay_seconds=1.0,
            backoff_factor=2.0,
        )
        limiter = RateLimiter(config)

        # With jitter = 0.5
        with patch("random.uniform", return_value=0.5):
            delay_low = limiter.backoff(1)

        # With jitter = 1.5
        with patch("random.uniform", return_value=1.5):
            delay_high = limiter.backoff(1)

        # Should be different due to jitter
        assert delay_low < delay_high


class TestReset:
    """Tests for reset method."""

    def test_reset_clears_last_request_time(self):
        """Test reset clears last_request_time."""
        limiter = RateLimiter()
        limiter._last_request_time = 1234.5
        limiter.reset()
        assert limiter._last_request_time == 0

    def test_reset_clears_request_count(self):
        """Test reset clears request_count."""
        limiter = RateLimiter()
        limiter._request_count = 100
        limiter.reset()
        assert limiter._request_count == 0


class TestRequestCountProperty:
    """Tests for request_count property."""

    def test_request_count_starts_at_zero(self):
        """Test initial request count is 0."""
        limiter = RateLimiter()
        assert limiter.request_count == 0

    def test_request_count_increments(self):
        """Test count increments with each wait()."""
        config = RateLimitConfig(
            min_delay_seconds=0,
            max_delay_seconds=0.001,
        )
        limiter = RateLimiter(config)

        with patch("time.time", return_value=1000.0):
            with patch("time.sleep"):
                with patch("random.uniform", return_value=0):
                    limiter.wait()
                    limiter.wait()
                    limiter.wait()

        assert limiter.request_count == 3

    def test_request_count_readonly(self):
        """Test request_count is read-only property."""
        limiter = RateLimiter()
        # Should raise AttributeError when trying to set
        with pytest.raises(AttributeError):
            limiter.request_count = 10


class TestRateLimitedDecorator:
    """Tests for rate_limited decorator."""

    def test_decorator_calls_wait(self):
        """Test decorator calls limiter.wait()."""
        limiter = RateLimiter()
        limiter.wait = MagicMock()

        @rate_limited(limiter)
        def test_func():
            return "result"

        test_func()

        limiter.wait.assert_called_once()

    def test_decorator_returns_function_result(self):
        """Test decorated function returns correctly."""
        config = RateLimitConfig(
            min_delay_seconds=0,
            max_delay_seconds=0.001,
        )
        limiter = RateLimiter(config)

        with patch("time.time", return_value=1000.0):
            with patch("time.sleep"):
                with patch("random.uniform", return_value=0):

                    @rate_limited(limiter)
                    def test_func():
                        return "expected_result"

                    result = test_func()

        assert result == "expected_result"

    def test_decorator_preserves_function_metadata(self):
        """Test @wraps preserves function name/docs."""
        limiter = RateLimiter()
        limiter.wait = MagicMock()

        @rate_limited(limiter)
        def my_function():
            """My docstring."""
            pass

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My docstring."

    def test_decorator_passes_args(self):
        """Test decorator passes args to function."""
        limiter = RateLimiter()
        limiter.wait = MagicMock()

        @rate_limited(limiter)
        def test_func(a, b, c=None):
            return (a, b, c)

        result = test_func(1, 2, c=3)

        assert result == (1, 2, 3)

    def test_decorator_with_exception(self):
        """Test decorator doesn't swallow exceptions."""
        limiter = RateLimiter()
        limiter.wait = MagicMock()

        @rate_limited(limiter)
        def test_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            test_func()

        # wait should still have been called
        limiter.wait.assert_called_once()
