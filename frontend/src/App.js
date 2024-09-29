import React, { useState, useEffect } from 'react';
import './App.css';

// Error handling function
const handleGooglePlayError = (error) => {
  if (error.message.includes('net::ERR_BLOCKED_BY_CLIENT')) {
    console.warn('A request to Google Play was blocked, likely by an ad-blocker. This won\'t affect the app\'s functionality.');
  } else if (error.message.includes('https://play.google.com/log')) {
    console.warn('A Google Play logging request was blocked. This won\'t affect the app\'s functionality.');
  } else {
    console.error('An error occurred:', error);
  }
};

// Add error event listener
window.addEventListener('error', (event) => {
  handleGooglePlayError(event.error);
});

function App() {
  const [podcasts, setPodcasts] = useState({ random: null, last: null });
  const [feedback, setFeedback] = useState('');
  const [experimentIdea, setExperimentIdea] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [isApiKeyValid, setIsApiKeyValid] = useState(false);
  const [selectedPodcast, setSelectedPodcast] = useState(null);
  const [hasVoted, setHasVoted] = useState(false);

  const API_BASE_URL = 'http://localhost:8000';

  useEffect(() => {
    const voted = localStorage.getItem('hasVoted');
    if (voted) {
      setHasVoted(true);
    }
    const storedApiKey = localStorage.getItem('apiKey');
    if (storedApiKey) {
      setApiKey(storedApiKey);
      validateApiKey(storedApiKey);
    }
  }, []);

  const handleApiKeyChange = (event) => {
    const newApiKey = event.target.value;
    setApiKey(newApiKey);
    validateApiKey(newApiKey);
    localStorage.setItem('apiKey', newApiKey);
  };

  const validateApiKey = async (key) => {
    if (!key) {
      setIsApiKeyValid(false);
      alert('Please enter an API key');
      return;
    }
    try {
      const response = await fetch(`${API_BASE_URL}/validate_api_key`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ api_key: key }),
        mode: 'cors', // Explicitly set CORS mode
      });
      const data = await response.json();
      if (response.ok) {
        setIsApiKeyValid(true);
        alert('API key is valid!');
      } else {
        setIsApiKeyValid(false);
        if (response.status === 401) {
          alert('Invalid API key: The provided API key is incorrect.');
        } else {
          alert(`Error validating API key: ${data.detail || 'Unknown error'}`);
        }
      }
    } catch (error) {
      console.error('Error:', error);
      setIsApiKeyValid(false);
      if (error.name === 'TypeError' && error.message === 'Failed to fetch') {
        alert('Network error: Unable to connect to the server. Please check if the backend is running and accessible.');
      } else {
        alert(`Error validating API key: ${error.message}`);
      }
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (file) {
      const formData = new FormData();
      formData.append('file', file);

      try {
        console.log('Attempting to upload file to:', `${API_BASE_URL}/upload_pdf`);
        const response = await fetch(`${API_BASE_URL}/upload_pdf`, {
          method: 'POST',
          body: formData,
          mode: 'cors',  // Explicitly set CORS mode
        });
        
        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
        }
        
        await response.json(); // We're not using the result, but we still want to await the response
        console.log("File uploaded:", file.name);
      } catch (error) {
        console.error('Error:', error);
        if (error.name === 'TypeError' && error.message === 'Failed to fetch') {
          alert('Network error: Unable to connect to the server. Please check if the backend is running and accessible.');
        } else {
          alert(`Error uploading PDF: ${error.message}`);
        }
      }
    }
  };

  const [error, setError] = useState(null);

  const handleCreatePodcasts = async () => {
    try {
      setError(null);
      const response = await fetch(`${API_BASE_URL}/create_podcasts`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ api_key: isApiKeyValid ? apiKey : null })
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Unknown error occurred');
      }
      const result = await response.json();
      setPodcasts({
        random: result.podcasts.find(p => p.type === 'random'),
        last: result.podcasts.find(p => p.type === 'last')
      });
      console.log('Podcasts created successfully!');
    } catch (error) {
      console.error('Error:', error);
      setError(`Error creating podcasts: ${error.message}`);
    }
  };

  const handlePodcastSelection = async (type) => {
    if (hasVoted) {
      alert("You have already voted.");
      return;
    }

    setSelectedPodcast(type);
    const timestamp = podcasts[type]?.timestamp;
    if (timestamp) {
      try {
        await fetch(`${API_BASE_URL}/vote`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ timestamp }),
        });
        setHasVoted(true);
        localStorage.setItem('hasVoted', 'true');
      } catch (error) {
        console.error('Error:', error);
        alert('Error recording vote');
      }
    }
  };

  const handleFeedbackSubmit = async (event) => {
    event.preventDefault();
    if (feedback && podcasts.last) {
      try {
        await fetch(`${API_BASE_URL}/process_feedback`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            podcast_state: podcasts.last,
            feedback: feedback,
            timestamp: podcasts.last.timestamp
          })
        });
        console.log("Feedback submitted:", feedback);
        setFeedback('');
      } catch (error) {
        console.error('Error:', error);
        alert('Error processing feedback');
      }
    }
  };

  const handleExperimentIdeaSubmit = (event) => {
    event.preventDefault();
    console.log("Experiment idea submitted:", experimentIdea);
    setExperimentIdea('');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 text-gray-200">
      <div className="w-full flex flex-col items-center justify-start min-h-screen pt-20 pb-12 px-4">
        <div className="text-center mb-16 max-w-6xl w-full">
          <h1 className="text-5xl sm:text-6xl md:text-7xl font-light mb-8 leading-tight">
            <span className="block">Welcome to the first</span>
            <span className="text-gray-300 whitespace-nowrap block mx-auto w-fit">
              Human-paced,&nbsp;World-scale,
            </span>
            <span className="text-gray-100 whitespace-nowrap block">
              Stochastic Gradient Descent
            </span>
          </h1>
          <p className="text-3xl sm:text-4xl md:text-5xl font-extralight">
            where <span className="font-normal text-blue-400 animate-pulse">you</span>{' '}
            <span className="font-normal">are the</span>{' '}

            <span className="font-normal text-blue-400 animate-pulse"> gradient</span>
          </p>
        </div>

        <div className="w-full max-w-6xl px-4">
          <div className="backdrop-blur-md bg-white/10 p-8 rounded-lg shadow-xl mb-8">
            <h2 className="text-4xl font-light text-center text-gray-100 mb-6">Create Your Podcasts</h2>
            {error && (
              <div className="bg-red-500 text-white p-4 rounded-md mb-4">
                {error}
              </div>
            )}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="space-y-4 md:col-span-3">
                <div className="flex flex-col md:flex-row md:space-x-4">
                  <div className="md:w-1/3 space-y-4">
                    <label className="block">
                      <span className="text-gray-300 text-xl">Upload your PDF</span>
                      <input
                        type="file"
                        accept=".pdf"
                        onChange={handleFileUpload}
                        className="mt-2 block w-full text-sm text-gray-300
                          file:mr-4 file:py-2 file:px-4
                          file:rounded-full file:border-0
                          file:text-sm file:font-light
                          file:bg-gray-700 file:text-gray-200
                          hover:file:bg-gray-600
                          cursor-pointer"
                      />
                    </label>
                    <button
                      onClick={handleCreatePodcasts}
                      className="w-full py-3 px-6 bg-gray-700 text-gray-200 rounded-md hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-opacity-50 transition duration-300 text-xl font-light"
                    >
                      Create Podcasts
                    </button>
                  </div>
                  <div className="md:w-2/3 space-y-4">
                    <h3 className="text-2xl font-light text-gray-100 mb-2">Podcast Playback</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="bg-gray-800 p-4 rounded-lg">
                        <h4 className="text-xl font-light text-gray-100 mb-2">Random Podcast</h4>
                        <audio 
                          controls 
                          className="w-full" 
                          src={podcasts.random?.audio_url || undefined}
                          disabled={!podcasts.random}
                        >
                          Your browser does not support the audio element.
                        </audio>
                      </div>
                      <div className="bg-gray-800 p-4 rounded-lg">
                        <h4 className="text-xl font-light text-gray-100 mb-2">Last Podcast</h4>
                        <audio 
                          controls 
                          className="w-full" 
                          src={podcasts.last?.audio_url || undefined}
                          disabled={!podcasts.last}
                        >
                          Your browser does not support the audio element.
                        </audio>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4 mt-4">
                      <button
                        onClick={() => handlePodcastSelection('random')}
                        disabled={hasVoted}
                        className={`w-full py-2 px-4 rounded-md transition duration-300 ${
                          selectedPodcast === 'random' ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-200 hover:bg-gray-600'
                        } ${hasVoted ? 'opacity-50 cursor-not-allowed' : ''}`}
                      >
                        Random is Better
                      </button>
                      <button
                        onClick={() => handlePodcastSelection('last')}
                        disabled={hasVoted}
                        className={`w-full py-2 px-4 rounded-md transition duration-300 ${
                          selectedPodcast === 'last' ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-200 hover:bg-gray-600'
                        } ${hasVoted ? 'opacity-50 cursor-not-allowed' : ''}`}
                      >
                        Last is Better
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-8">
              <div className="space-y-4">
                <p className="text-lg text-gray-200">Please provide your own OpenAI key if possible, I am just a poor postdoc. Each podcast costs around 20-30 cents with the feedback application.</p>
                <p className="text-red-500 text-lg font-bold">We don't keep any keys</p>
                <div className="flex flex-col space-y-2">
                  <input
                    type="text"
                    placeholder="Enter your OpenAI API key"
                    value={apiKey}
                    onChange={handleApiKeyChange}
                    className={`w-full p-3 bg-gray-800/50 text-gray-200 text-xl rounded-md border ${
                      isApiKeyValid ? 'border-green-500' : 'border-gray-700'
                    } focus:border-gray-500 focus:ring focus:ring-gray-500 focus:ring-opacity-50`}
                  />
                  <button
                    onClick={() => validateApiKey(apiKey)}
                    className={`w-full py-3 px-4 text-gray-200 text-xl rounded-md focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-opacity-50 transition duration-300 ${
                      isApiKeyValid
                        ? 'bg-green-600 hover:bg-green-700'
                        : 'bg-gray-700 hover:bg-gray-600'
                    }`}
                  >
                    {isApiKeyValid ? 'API Key Valid' : 'Validate Key'}
                  </button>
                </div>
              </div>
              <form onSubmit={handleFeedbackSubmit} className="space-y-4 md:col-span-2">
                <h3 className="text-xl font-light text-gray-100">Provide feedback for the Last podcast to generate gradient</h3>
                <p className="text-red-500 text-sm">Please provide feedback only if you think it's necessary</p>
                <textarea
                  value={feedback}
                  onChange={(e) => setFeedback(e.target.value)}
                  placeholder="Share your thoughts on the Last podcast..."
                  className="w-full p-3 bg-gray-800/50 text-gray-200 rounded-md border border-gray-700 focus:border-gray-500 focus:ring focus:ring-gray-500 focus:ring-opacity-50"
                  rows={4}
                />
                <button
                  type="submit"
                  className="w-full py-3 px-6 bg-gray-700 text-gray-200 rounded-md hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-opacity-50 transition duration-300 text-xl font-light"
                >
                  Send Feedback
                </button>
              </form>
            </div>
          </div>

          <div className="mt-8 space-y-6 backdrop-blur-md bg-white/10 p-8 rounded-lg shadow-xl">
            <h3 className="text-3xl font-light text-gray-100 mb-4">Learn More</h3>
            <p className="text-xl text-gray-300 mb-6">If you want to learn about the specific idea, watch the left video. If you want to learn more about text grad, watch the right video.</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div className="space-y-6">
                <div className="aspect-w-16 aspect-h-9">
                  <iframe
                    src="https://www.youtube-nocookie.com/embed/8jIbgJfP0Dw"
                    title="Specific Idea Video"
                    frameBorder="0"
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                    allowFullScreen
                    className="w-full h-full rounded-md"
                  ></iframe>
                </div>
              </div>
              <div className="space-y-6">
                <div className="aspect-w-16 aspect-h-9">
                  <iframe
                    src="https://www.youtube-nocookie.com/embed/Qks4UEsRwl0?start=2206"
                    title="Text Grad Video"
                    frameBorder="0"
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                    allowFullScreen
                    className="w-full h-full rounded-md"
                  ></iframe>
                </div>
              </div>
            </div>
          </div>
          <div className="mt-8 space-y-6 backdrop-blur-md bg-white/10 p-8 rounded-lg shadow-xl">
            <h3 className="text-3xl font-light text-gray-100">How you can help</h3>
            <p className="text-xl text-gray-300 mb-6">
              There are many ways to support this experiment, and I will appreciate every single one. The most important is by sharing or starring my git repo. If I get visibility, I will go for some minor sponsorships to add better TTS like ElevenLabs or some custom TTS on HuggingFace. If you are a front-end developer, you can support by turning this monstrosity of a page into something visually appealing. If this goes well, I a) will put more features like adding questions for the text before the podcast creation where you want the podcast to focus, b) Make some interactive podcast where you can interrupt and ask questions. Also, please provide feedback for the project or ideas for other world-scale gradient descent experiments.
            </p>
            <h4 className="text-2xl font-light text-gray-100 mt-6">Submit Experiment Ideas</h4>
            <form onSubmit={handleExperimentIdeaSubmit} className="space-y-6">
              <textarea
                value={experimentIdea}
                onChange={(e) => setExperimentIdea(e.target.value)}
                placeholder="Share your experiment ideas..."
                className="w-full p-3 bg-gray-800/50 text-gray-200 rounded-md border border-gray-700 focus:border-gray-500 focus:ring focus:ring-gray-500 focus:ring-opacity-50"
                rows={4}
              />
              <button
                type="submit"
                className="w-full py-3 px-6 bg-gray-700 text-gray-200 rounded-md hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-opacity-50 transition duration-300 text-xl font-light"
              >
                Submit Idea
              </button>
            </form>
          </div>
          <div className="mt-8 space-y-6 backdrop-blur-md bg-white/10 p-8 rounded-lg shadow-xl">
            <h3 className="text-3xl font-light text-gray-100">Acknowledgments</h3>
            <p className="text-xl text-gray-300 mb-6">
              This entire application was created with the assistance of <a href="https://aider.chat/" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300">aider</a>, an AI-powered coding assistant. We'd like to express our gratitude to the aider team for their innovative tool that made this project possible.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
