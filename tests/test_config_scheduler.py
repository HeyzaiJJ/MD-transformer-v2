from concurrent.futures import Future
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from md_transformer.config import load_config, check_service
from md_transformer.scheduler import run_batch


class RegressionTests(unittest.TestCase):
    def test_config_requires_file_and_values(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / '.env'
            with self.assertRaises(ValueError):
                load_config(path)
            path.write_text('', encoding='utf-8')
            with self.assertRaises(ValueError):
                load_config(path)
            path.write_text('SURYA_INFERENCE_URL=http://192.168.11.13:8456\nVLLM_API_KEY=test-secret\n', encoding='utf-8-sig')
            with patch.dict('os.environ', {'SURYA_INFERENCE_URL': 'http://127.0.0.1:8456'}):
                config = load_config(path)
            self.assertEqual(config['surya_url'], 'http://192.168.11.13:8456/v1')
            self.assertEqual(config['concurrency'], 5)
            self.assertEqual(config['requests_per_worker'], 8)
            path.write_text(path.read_text(encoding='utf-8-sig') + 'CONCURRENCY=no\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                load_config(path)

    def test_service_errors_hide_key(self):
        with patch('md_transformer.config.httpx.Client') as client:
            get = client.return_value.__enter__.return_value.get
            get.return_value.status_code = 401
            with self.assertRaisesRegex(ValueError, '\u8ba4\u8bc1\u5931\u8d25') as error:
                check_service('http://host/v1', 'secret-key')
            self.assertNotIn('secret-key', str(error.exception))
            get.side_effect = httpx.ConnectError('connection refused')
            with self.assertRaisesRegex(ValueError, '\u65e0\u6cd5\u8fde\u63a5'):
                check_service('http://host/v1', 'secret-key')

    def test_fixed_pool_continues_after_oom_without_retry(self):
        jobs = [(Path(str(i)), Path(str(i))) for i in range(13)]
        submitted = []
        def submit(fn, source, target, mode):
            submitted.append(source)
            future = Future()
            if source == '1':
                future.set_exception(RuntimeError('CUDA out of memory'))
            elif source == '2':
                future.set_exception(ValueError('bad PDF'))
            else:
                future.set_result((source, 1))
            return future
        with patch('md_transformer.scheduler.ProcessPoolExecutor') as pool:
            pool.return_value.__enter__.return_value.submit.side_effect = submit
            success, failed, oom = run_batch(jobs, mode='balanced', concurrency=5, requests_per_worker=8,
                                             surya_url='http://host/v1', api_key='test')
        self.assertEqual(pool.call_count, 1)
        self.assertEqual(pool.call_args.kwargs['max_workers'], 5)
        self.assertEqual(pool.call_args.kwargs['initargs'], ('http://host/v1', 'test', 'balanced', 8))
        self.assertEqual(len(submitted), 13)
        self.assertEqual(len(set(submitted)), 13)
        self.assertEqual((len(success), len(failed), oom), (11, 2, 1))

    def test_empty_batch_does_not_create_pool(self):
        with patch('md_transformer.scheduler.ProcessPoolExecutor') as pool:
            self.assertEqual(run_batch([], mode='balanced', concurrency=5, requests_per_worker=8,
                             surya_url='http://host/v1', api_key='test'), ([], {}, 0))
            pool.assert_not_called()


if __name__ == '__main__':
    unittest.main()
