/// <reference types="jest" />

import { RAGApi } from '../api/RAGApi';

describe('RAGApi', () => {
    let api: RAGApi;
    const mockBaseUrl = 'http://localhost:8000';
    const mockApiKey = 'test-api-key';

    beforeEach(() => {
        api = new RAGApi(mockBaseUrl, mockApiKey);
        (global.fetch as jest.Mock).mockClear();
    });

    describe('search', () => {
        it('should make a POST request to the search endpoint', async () => {
            const mockResponse = {
                results: [
                    {
                        content: 'Test content',
                        source: 'test.md',
                        similarity: 0.95
                    }
                ]
            };

            (global.fetch as jest.Mock).mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve(mockResponse)
            });

            const query = 'test query';
            const maxResults = 5;
            const result = await api.search(query, maxResults);

            expect(global.fetch).toHaveBeenCalledWith(
                `${mockBaseUrl}/search`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${mockApiKey}`
                    },
                    body: JSON.stringify({ query, max_results: maxResults })
                }
            );

            expect(result).toEqual(mockResponse);
        });

        it('should handle API errors', async () => {
            (global.fetch as jest.Mock).mockResolvedValueOnce({
                ok: false,
                statusText: 'Internal Server Error'
            });

            await expect(api.search('test')).rejects.toThrow('API request failed: Internal Server Error');
        });
    });
}); 