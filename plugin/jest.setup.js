require('@testing-library/jest-dom');

// Mock fetch globally
global.fetch = jest.fn();

// Mock URL
global.URL.createObjectURL = jest.fn();

// Reset all mocks before each test
beforeEach(() => {
    jest.clearAllMocks();
}); 