import { afterEach, expect, it, vi } from 'vitest';
import { api, jsonBody } from './api';

afterEach(() => vi.unstubAllGlobals());

it('sends the API key only as an authorization header', () => {
  const options = jsonBody({ message: 'hi' }, 'test-key');
  expect(options.headers).toMatchObject({ Authorization: 'Bearer test-key' });
  expect(options.body).not.toContain('test-key');
});

it('surfaces the backend error instead of treating it as an answer', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, json: async () => ({ error: 'Key không hợp lệ' }) }));
  await expect(api('/chat')).rejects.toThrow('Key không hợp lệ');
});
