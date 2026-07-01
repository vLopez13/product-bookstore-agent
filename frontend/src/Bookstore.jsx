// Bookstore javascxx
import React, { useState, useEffect } from 'react';
import Vapi from '@vapi-ai/web';
import './Bookstore.css';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseKey = import.meta.env.VITE_SUPABASE_KEY;
const supabase = createClient(supabaseUrl, supabaseKey);
const vapi = new Vapi(import.meta.env.VITE_VAPI_KEY);
export default function Bookstore() {
  
  const [session, setSession] = useState(null);
  const [email, setEmail] = useState('');
  const [authLoading, setAuthLoading] = useState(false);
  const [authMessage, setAuthMessage] = useState('');
  //bookstore states 
  const [isCallActive, setIsCallActive] = useState(false);
  const [books, setBooks] = useState([]);

  useEffect(() => {
  
    vapi.on('call-start', () => setIsCallActive(true));
    vapi.on('call-end', () => {
      setIsCallActive(false);
      setBooks([]); 
    });
    
    supabase.auth.getSession().then(({ data: { session } }) => {
    setSession(session);
    });
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
    });
    
    vapi.on('message', (message) => {
      if (message.type === 'tool-call-results') {
        const toolCall = message.toolCallResults[0];
        
        if (toolCall && toolCall.result) {
          try {
            const serverData = JSON.parse(toolCall.result);
            if (serverData.books) {
              setBooks(serverData.books);
            }
          } catch (error) {
            console.error("Failed to parse book data:", error);
          }
        }
      }
    });

    return () => {
      vapi.removeAllListeners();
      subscription.unsubscribe();
    };
  }, []);

const handleLogin = async (e) => {
    e.preventDefault();
    setAuthLoading(true);
    setAuthMessage('');

    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: {

        emailRedirectTo: window.location.origin, 
      },
    });

    if (error) {
      setAuthMessage(error.message);
    } else {
      setAuthMessage('Magic link sent! Please check your inbox.');
    }
    setAuthLoading(false);
  };

  const handleLogout = async () => {
    await supabase.auth.signOut();
  };

  // 3. Start the conversation
  const toggleCall = () => {
    if (isCallActive) {
      vapi.stop();
    } else {
      vapi.start("YOUR_VAPI_ASSISTANT_ID");
    }
  };

  // 4. Handle visual clicks
  const handleBuyClick = (bookId, bookTitle) => {
    console.log(`User selected: ${bookTitle}`);
    
    vapi.send({
      type: 'add-message',
      message: {
        role: 'user',
        content: `I clicked the button on my screen to buy the book "${bookTitle}" with ID ${bookId}. Please proceed with my order and collect my delivery information.`
      }
    });
    
    setBooks([]);
  };


  if (!session) {
    return (
      <div className="store-wrapper">
        <div className="main-box" style={{ maxWidth: '400px', margin: '0 auto', textAlign: 'center' }}>
          <div className="header-box">
            <h2 className="header-title">Welcome to AI Bookstore</h2>
            <p className="header-subtitle">Enter your email to enter</p>
          </div>
          <div className="content-box">
            <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
              <input
                type="email"
                placeholder="hello@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                style={{ padding: '10px', borderRadius: '5px', border: '1px solid #ccc' }}
              />
              <button 
                type="submit" 
                className="btn btn-primary" 
                disabled={authLoading}
              >
                {authLoading ? 'Sending...' : 'Send Magic Link'}
              </button>
            </form>
            {authMessage && <p style={{ marginTop: '15px', color: '#555' }}>{authMessage}</p>}
          </div>
        </div>
      </div>
    );
  }
 return (
    <div className="store-wrapper">
      {/* Main Container Box */}
      <div className="main-box">
        
        {/* Header Box */}
        <div className="header-box">
          <div>
            <h2 className="header-title">AI Bookstore</h2>
            <p className="header-subtitle">Voice-activated catalog and checkout</p>
            <p style={{ fontSize: '12px', color: 'gray' }}>Logged in as: {session.user.email}</p>
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            <button 
              onClick={toggleCall}
              className={`btn ${isCallActive ? 'btn-danger' : 'btn-primary'}`}
            >
              {isCallActive ? 'End Conversation' : 'Talk to AI Assistant'}
            </button>
            <button onClick={handleLogout} className="btn btn-secondary">
              Logout
            </button>
          </div>
        </div>

        {/* Content Box */}
        <div className="content-box">
          
          {books.length === 0 && !isCallActive && (
            <div className="empty-state">
              <p>Click "Talk to AI Assistant" to start searching for books.</p>
            </div>
          )}

          {books.length === 0 && isCallActive && (
            <div className="listening-state">
              <p>Listening... Ask LitReads AI to find a book.</p>
            </div>
          )}

          {/* Render the book cards dynamically */}
          {books.length > 0 && (
            <div className="book-grid">
              {books.map((book) => (
                <div key={book.id} className="book-card">
                  <div>
                    <h3 className="book-title">{book.title}</h3>
                    <p className="book-price">${book.price.toFixed(2)}</p>
                  </div>
                  
                  <button 
                    onClick={() => handleBuyClick(book.id, book.title)}
                    className="btn btn-secondary"
                  >
                    Buy This Book!
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}