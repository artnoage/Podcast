import React, { useState, useEffect } from 'react';
import { createPodcasts, submitVote, submitFeedback, submitExperimentIdea } from './api';
import './App.css';
import LoadingSpinner from './LoadingSpinner';

// New state variable for feedback box
const FEEDBACK_STATES = {
  DISABLED: 'DISABLED',
  ENABLED: 'ENABLED',
  THANK_YOU: 'THANK_YOU',
};

// New state variable for voting buttons
const VOTE_STATES = {
  DISABLED: 'DISABLED',
  ENABLED: 'ENABLED',
  VOTED: 'VOTED',
};

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
  const [selectedPodcast, setSelectedPodcast] = useState(null);
  const [voteState, setVoteState] = useState(VOTE_STATES.DISABLED);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [newTimestamp, setNewTimestamp] = useState(null);
  const [feedbackState, setFeedbackState] = useState(FEEDBACK_STATES.DISABLED);
  const [progress, setProgress] = useState('');
  const [pdfFile, setPdfFile] = useState(null);
  useEffect(() => {
    const voted = localStorage.getItem('hasVoted');
    if (voted) {
      setVoteState(VOTE_STATES.VOTED);
    }
  }, []);

  useEffect(() => {
    if (podcasts.random && podcasts.last) {
      localStorage.removeItem('hasVoted');
      setVoteState(VOTE_STATES.ENABLED);
    }
  }, [podcasts]);


  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (file && file.type === 'application/pdf') {
      setPdfFile(file);
      console.log("File selected:", file.name);
    } else {
      setError("Please select a valid PDF file.");
    }
  };

  const handleCreatePodcasts = async () => {
    if (!pdfFile) {
      setError("Please upload a PDF file first.");
      return;
    }
    try {
      setError(null);
      setIsLoading(true);
      setProgress("Initiating podcast creation...");
      console.log('Creating podcasts.');

      const result = await createPodcasts(
        pdfFile,
        (progressData) => {
          console.log('Progress update:', progressData);
          setProgress(`Processing... ${progressData.status}`);
        }
      );

      console.log('Podcasts created successfully:', result);
      setProgress("Podcasts created successfully!");

      if (result.podcasts && result.podcasts.length === 2) {
        const randomPodcast = result.podcasts.find(p => p.type === 'random');
        const lastPodcast = result.podcasts.find(p => p.type === 'last');

        // Create Blobs and URLs for the audio data
        const randomAudioBlob = new Blob([randomPodcast.audio_data], { type: 'audio/mpeg' });
        const lastAudioBlob = new Blob([lastPodcast.audio_data], { type: 'audio/mpeg' });

        setPodcasts({
          random: {
            ...randomPodcast,
            audio_url: URL.createObjectURL(randomAudioBlob)
          },
          last: {
            ...lastPodcast,
            audio_url: URL.createObjectURL(lastAudioBlob)
          }
        });

        if (lastPodcast?.new_timestamp) {
          setNewTimestamp(lastPodcast.new_timestamp);
        }
        setVoteState(VOTE_STATES.ENABLED);
        localStorage.removeItem('hasVoted');
        setFeedbackState(FEEDBACK_STATES.ENABLED);
      } else {
        throw new Error('Incorrect number of podcasts returned from the server');
      }
    } catch (error) {
      console.error('Error creating podcasts:', error);
      setError(`Error creating podcasts: ${error.message}`);
      setProgress("Podcast creation failed.");
    } finally {
      setIsLoading(false);
    }
  };


  const handlePodcastSelection = async (type) => {
    if (voteState !== VOTE_STATES.ENABLED) {
      return;
    }

    setSelectedPodcast(type);
    const timestamp = podcasts[type]?.timestamp;
    try {
      const result = await submitVote(timestamp);
      console.log("Vote submitted successfully:", result);
      setVoteState(VOTE_STATES.VOTED);
      localStorage.setItem('hasVoted', 'true');
    } catch (error) {
      console.error('Error:', error);
      alert('Error recording vote: ' + error.message);
    }
  };

  const handleFeedbackSubmit = (event) => {
    event.preventDefault();
    if (feedback && newTimestamp) {
      const oldTimestamp = podcasts.last ? podcasts.last.timestamp : null;
      submitFeedback(feedback, oldTimestamp, newTimestamp)
        .catch(error => console.error('Error submitting feedback:', error));
      console.log("Feedback submitted:", feedback);
      setFeedbackState(FEEDBACK_STATES.THANK_YOU);
      setTimeout(() => {
        setFeedbackState(FEEDBACK_STATES.DISABLED);
        setFeedback('');
      }, 3000); // Reset after 3 seconds
    } else {
      alert('Please ensure you have created podcasts and provided feedback before submitting.');
    }
  };

  const handleExperimentIdeaSubmit = async (event) => {
    event.preventDefault();
    try {
      await submitExperimentIdea(experimentIdea);
      console.log("Experiment idea submitted:", experimentIdea);
      setExperimentIdea('');
      alert('Thank you for submitting your experiment idea!');
    } catch (error) {
      console.error('Error submitting experiment idea:', error);
      alert('Error submitting experiment idea. Please try again.');
    }
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
            <div className="mt-8">
              <h3 className="text-2xl font-light text-gray-100 mb-4">Upload Your PDF</h3>
              <div 
                className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center"
                onDragOver={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                }}
                onDrop={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  const files = e.dataTransfer.files;
                  if (files.length) {
                    handleFileUpload({ target: { files: [files[0]] } });
                  }
                }}
              >
                <input
                  type="file"
                  accept=".pdf"
                  onChange={handleFileUpload}
                  className="hidden"
                  id="file-upload"
                />
                <label 
                  htmlFor="file-upload"
                  className="cursor-pointer text-gray-300 hover:text-gray-100"
                >
                  <span className="text-xl">Drag and drop your PDF here, or click to select a file</span>
                </label>
                {pdfFile && (
                  <p className="mt-2 text-gray-300">Selected file: {pdfFile.name}</p>
                )}
              </div>
              {progress && (
                <div className="mt-2 text-sm text-gray-300">{progress}</div>
              )}
              <button
                onClick={handleCreatePodcasts}
                className="w-full mt-4 py-2 px-4 bg-gray-700 text-gray-200 rounded-md hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-opacity-50 transition duration-300 text-xl font-light"
                disabled={isLoading || !pdfFile}
              >
                {isLoading ? <LoadingSpinner /> : 'Create Podcasts'}
              </button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
              <div className="space-y-4 md:col-span-3">
                <div className="flex flex-col md:flex-row md:space-x-4">
                  <div className="md:w-full space-y-4">
                    <h3 className="text-2xl font-light text-gray-100 mb-2">Podcast Playback</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="bg-gray-800 p-4 rounded-lg">
                        <h4 className="text-xl font-light text-gray-100 mb-2">Random Podcast</h4>
                        {podcasts.random && podcasts.random.audio_url ? (
                          <>
                            <audio 
                              controls 
                              className="w-full" 
                              src={podcasts.random.audio_url}
                            >
                              Your browser does not support the audio element.
                            </audio>
                            <div className="flex justify-between mt-2">
                              <button
                                onClick={() => {
                                  URL.revokeObjectURL(podcasts.random.audio_url);
                                  setPodcasts(prev => ({...prev, random: {...prev.random, audio_url: null}}));
                                }}
                                className="text-sm text-gray-400 hover:text-gray-300"
                              >
                                Release audio memory
                              </button>
                              <a
                                href={podcasts.random.audio_url}
                                download="random_podcast.mp3"
                                className="text-sm text-blue-400 hover:text-blue-300"
                              >
                                Download
                              </a>
                            </div>
                          </>
                        ) : (
                          <p className="text-gray-400">No audio available</p>
                        )}
                      </div>
                      <div className="bg-gray-800 p-4 rounded-lg">
                        <h4 className="text-xl font-light text-gray-100 mb-2">Last Podcast</h4>
                        {podcasts.last && podcasts.last.audio_url ? (
                          <>
                            <audio 
                              controls 
                              className="w-full" 
                              src={podcasts.last.audio_url}
                            >
                              Your browser does not support the audio element.
                            </audio>
                            <div className="flex justify-between mt-2">
                              <button
                                onClick={() => {
                                  URL.revokeObjectURL(podcasts.last.audio_url);
                                  setPodcasts(prev => ({...prev, last: {...prev.last, audio_url: null}}));
                                }}
                                className="text-sm text-gray-400 hover:text-gray-300"
                              >
                                Release audio memory
                              </button>
                              <a
                                href={podcasts.last.audio_url}
                                download="last_podcast.mp3"
                                className="text-sm text-blue-400 hover:text-blue-300"
                              >
                                Download
                              </a>
                            </div>
                          </>
                        ) : (
                          <p className="text-gray-400">No audio available</p>
                        )}
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4 mt-4">
                      <button
                        onClick={() => handlePodcastSelection('random')}
                        disabled={voteState !== VOTE_STATES.ENABLED}
                        className={`w-full py-2 px-4 rounded-md transition duration-300 ${
                          selectedPodcast === 'random' ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-200 hover:bg-gray-600'
                        } ${voteState !== VOTE_STATES.ENABLED ? 'opacity-50 cursor-not-allowed' : ''}`}
                      >
                        Random is Better
                      </button>
                      <button
                        onClick={() => handlePodcastSelection('last')}
                        disabled={voteState !== VOTE_STATES.ENABLED}
                        className={`w-full py-2 px-4 rounded-md transition duration-300 ${
                          selectedPodcast === 'last' ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-200 hover:bg-gray-600'
                        } ${voteState !== VOTE_STATES.ENABLED ? 'opacity-50 cursor-not-allowed' : ''}`}
                      >
                        Last is Better
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div className="mt-8">
              <form onSubmit={handleFeedbackSubmit} className="space-y-4">
                <h3 className="text-xl font-light text-gray-100">Provide feedback for the Last podcast to generate gradient</h3>
                <p className="text-red-500 text-sm">Please provide feedback only if you think it's necessary</p>
                {feedbackState === FEEDBACK_STATES.THANK_YOU ? (
                  <div className="w-full p-3 bg-green-600 text-white rounded-md">
                    Thanks for the feedback! You were a helpful gradient. Have a nice day!
                  </div>
                ) : (
                  <>
                    <textarea
                      value={feedback}
                      onChange={(e) => setFeedback(e.target.value)}
                      placeholder="Share your thoughts on the Last podcast..."
                      className="w-full p-3 bg-gray-800/50 text-gray-200 rounded-md border border-gray-700 focus:border-gray-500 focus:ring focus:ring-gray-500 focus:ring-opacity-50"
                      rows={6}
                      disabled={feedbackState === FEEDBACK_STATES.DISABLED}
                    />
                    <button
                      type="submit"
                      className={`w-full py-3 px-6 bg-gray-700 text-gray-200 rounded-md hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-opacity-50 transition duration-300 text-xl font-light ${
                        feedbackState === FEEDBACK_STATES.DISABLED ? 'opacity-50 cursor-not-allowed' : ''
                      }`}
                      disabled={feedbackState === FEEDBACK_STATES.DISABLED}
                    >
                      Send Feedback
                    </button>
                  </>
                )}
              </form>
            </div>
          </div>
  
          <div className="mt-8 space-y-6 backdrop-blur-md bg-white/10 p-8 rounded-lg shadow-xl">
            <h3 className="text-3xl font-light text-gray-100 mb-4">Learn More</h3>
            <p className="text-xl text-gray-300 mb-6">If you want to learn about the specific idea, watch the left video. If you want to learn more about text grad, watch the right video (pan inteded).</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div className="space-y-6">
                <div className="aspect-w-16 aspect-h-9">
                  <iframe
                    src="https://www.youtube-nocookie.com/embed/c2W2VNZQBi4"
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
              There are many ways to support this experiment, and I will appreciate every single one. The most important is by forking or starring my <a href="https://github.com/artnoage/Podcast.git" className="text-blue-400 hover:text-blue-300">git repo</a>. If I get visibility, 
              I will go for some minor sponsorships to add better TTS like ElevenLabs or some custom TTS on HuggingFace. If you are a front-end developer, you can support by turning this monstrosity of a page into something visually appealing. 
              If this goes well, I a) will put more features like adding questions for the text before the podcast creation where you want the podcast to focus, b) Make some interactive podcast where you can interrupt and ask questions. 
              Also, please provide feedback for the project or ideas for other world-scale gradient descent experiments.
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
              This entire application was created with the assistance of <a href="https://aider.chat/" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300">aider</a>, an AI-powered coding assistant. 
              I want to thank <a href="https://www.youtube.com/@AICodeKing" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300">AICodeKing</a> that introduced me to it. For this project, I used <a href="https://www.langchain.com/langgraph" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300">LangGraph</a> and <a href="https://textgrad.com/" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300">TextGrad</a>. The site design was created using <a href="https://v0.dev/chat" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300">v0.dev</a>. I also want to mention some of my favorite AI YouTubers that somehow influenced this project:
            </p>
            <ol className="list-decimal list-inside space-y-2 text-xl text-gray-300">
              <li><a href="https://www.youtube.com/channel/UCfOvNb3xj28SNqPQ_JIbumg" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300">Discover AI</a></li>
              <li><a href="https://www.youtube.com/channel/UCHsThxa9HvDpSywv4bP55NA" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300">J. Gravelles</a></li>
              <li><a href="https://www.youtube.com/channel/UC6MhHkSosYXAD-LTXBWyLMg" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300">Neural Breakdown with AVB</a></li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  );
} 
export default App;
