const API_BASE_URL = 'https://fastapi.metaskepsis.com'; // Replace with your API base URL


export const createPodcasts = (pdfFile, onProgress) => {
  return new Promise((resolve, reject) => {
    console.log('createPodcasts called with:', { pdfFile: pdfFile.name });
    const formData = new FormData();
    formData.append('pdf_content', pdfFile);
    formData.append('summarizer_model', 'gpt-4o-mini');
    formData.append('scriptwriter_model', 'gpt-4o-mini');
    formData.append('enhancer_model', 'gpt-4o-mini');
    formData.append('provider', 'OpenAI');

    fetch(`${API_BASE_URL}/create_podcasts`, {
      method: 'POST',
      body: formData,
    }).then(response => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    }).then(data => {
      const taskId = data.task_id;
      console.log('Podcast creation started, task ID:', taskId);
      
      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await fetch(`${API_BASE_URL}/podcast_status/${taskId}`);
          if (!statusResponse.ok) {
            throw new Error(`HTTP error! status: ${statusResponse.status}`);
          }
          const statusData = await statusResponse.json();
          console.log('Podcast status:', statusData);

          if (statusData.status === 'completed') {
            clearInterval(pollInterval);
            // Fetch the audio data for both podcasts
            const randomAudioResponse = await fetch(`${API_BASE_URL}/get_podcast_audio/${taskId}/random`);
            const lastAudioResponse = await fetch(`${API_BASE_URL}/get_podcast_audio/${taskId}/last`);
            
            if (!randomAudioResponse.ok || !lastAudioResponse.ok) {
              throw new Error(`HTTP error! status: ${randomAudioResponse.status} or ${lastAudioResponse.status}`);
            }
            
            const randomAudioData = await randomAudioResponse.arrayBuffer();
            const lastAudioData = await lastAudioResponse.arrayBuffer();
            
            // Add audio data to the result
            statusData.result.podcasts = statusData.result.podcasts.map(podcast => ({
              ...podcast,
              audio_data: podcast.type === 'random' ? randomAudioData : lastAudioData
            }));
            resolve(statusData.result);
          } else if (statusData.status === 'failed') {
            clearInterval(pollInterval);
            reject(new Error(statusData.error || 'Podcast creation failed'));
          } else if (onProgress) {
            onProgress(statusData);
          }
        } catch (error) {
          console.error('Error polling podcast status:', error);
          clearInterval(pollInterval);
          reject(error);
        }
      }, 5000); // Poll every 5 seconds
    }).catch(error => {
      console.error('Error in createPodcasts:', error);
      reject(error);
    });
  });
};


export const submitVote = async (timestamp) => {
  const response = await fetch(`${API_BASE_URL}/vote`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ timestamp: timestamp === null ? "original" : timestamp }),
  });
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Error recording vote');
  }
  return await response.json();
};

export const submitFeedback = async (feedback, oldTimestamp, newTimestamp) => {
  try {
    const response = await fetch(`${API_BASE_URL}/process_feedback`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        feedback: feedback,
        old_timestamp: oldTimestamp || null,
        new_timestamp: newTimestamp
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Error submitting feedback');
    }

    return await response.json();
  } catch (error) {
    console.error('Error submitting feedback:', error);
    throw error;
  }
};

export const submitExperimentIdea = async (idea) => {
  try {
    const response = await fetch(`${API_BASE_URL}/submit_experiment_idea`, {
      method: 'POST',
      headers: {
        'Content-Type': 'text/plain',
      },
      body: idea,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || 'Error submitting experiment idea');
    }

    return await response.json();
  } catch (error) {
    console.error('Error submitting experiment idea:', error);
    throw error;
  }
};

