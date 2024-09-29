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

export const createPodcasts = async (apiKey, pdfFile) => {
  try {
    console.log('Creating podcasts with API key:', apiKey ? 'API key provided' : 'No API key');
    const formData = new FormData();
    formData.append('api_key', apiKey || '');
    formData.append('pdf_content', pdfFile);
    const response = await fetch(`${API_BASE_URL}/create_podcasts`, {
      method: 'POST',
      body: formData
    });
    if (!response.ok) {
      const errorData = await response.json();
      console.error('Error response:', errorData);
      throw new Error(errorData.detail || 'Unknown error occurred');
    }
    const result = await response.json();
    console.log('Podcasts created successfully:', result);

    // Process audio segments for each podcast
    result.podcasts = result.podcasts.map(podcast => {
      const audioBlob = new Blob(podcast.audio_segments, { type: 'audio/mpeg' });
      const audioUrl = URL.createObjectURL(audioBlob);
      return { ...podcast, audio_url: audioUrl };
    });

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

export const submitFeedback = async (feedback, oldTimestamp, newTimestamp) => {
  const response = await fetch(`${API_BASE_URL}/process_feedback`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      feedback: feedback,
      old_timestamp: oldTimestamp,
      new_timestamp: newTimestamp
    })
  });
  if (!response.ok) {
    throw new Error('Error processing feedback');
  }
};
