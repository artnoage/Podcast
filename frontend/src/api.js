const API_BASE_URL = 'http://localhost:8000';

export const validateApiKey = async (apiKey) => {
  if (!apiKey) {
    throw new Error('Please enter an API key');
  }
  const response = await fetch(`${API_BASE_URL}/validate_api_key`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ api_key: apiKey }),
    mode: 'cors',
  });
  if (!response.ok) {
    const data = await response.json();
    throw new Error(data.detail || 'Error validating API key');
  }
  return true;
};

export const uploadFile = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await fetch(`${API_BASE_URL}/upload_pdf`, {
    method: 'POST',
    body: formData,
    mode: 'cors',
  });
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
  }
  return response.json();
};

export const createPodcasts = async (apiKey) => {
  try {
    console.log('Creating podcasts with API key:', apiKey ? 'API key provided' : 'No API key');
    const response = await fetch(`${API_BASE_URL}/create_podcasts`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ api_key: apiKey || null })
    });
    if (!response.ok) {
      const errorData = await response.json();
      console.error('Error response:', errorData);
      throw new Error(errorData.detail || 'Unknown error occurred');
    }
    const result = await response.json();
    console.log('Podcasts created successfully:', result);
    return result;
  } catch (error) {
    console.error('Error creating podcasts:', error);
    throw error;
  }
};

export const submitVote = async (timestamp) => {
  const response = await fetch(`${API_BASE_URL}/vote`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ timestamp }),
  });
  if (!response.ok) {
    throw new Error('Error recording vote');
  }
};

export const submitFeedback = async (podcastState, feedback, timestamp) => {
  const response = await fetch(`${API_BASE_URL}/process_feedback`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      podcast_state: podcastState,
      feedback: feedback,
      timestamp: timestamp
    })
  });
  if (!response.ok) {
    throw new Error('Error processing feedback');
  }
};
