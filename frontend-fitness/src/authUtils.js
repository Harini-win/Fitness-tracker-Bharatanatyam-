export const getAuthToken = () => {
    const token = localStorage.getItem('authToken') || 
                  localStorage.getItem('token') || 
                  sessionStorage.getItem('authToken') ||
                  sessionStorage.getItem('token');
    
    console.log('Retrieved token:', token ? 'Token found' : 'No token found');
    return token;
};

export const setAuthToken = (token) => {
    localStorage.setItem('authToken', token);
    console.log('Token stored');
};

export const removeAuthToken = () => {
    localStorage.removeItem('authToken');
    localStorage.removeItem('token');
    sessionStorage.removeItem('authToken');
    sessionStorage.removeItem('token');
    console.log('Tokens cleared');
};