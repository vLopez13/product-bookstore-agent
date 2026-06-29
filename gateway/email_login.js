import { createClient } from '@supabase/supabase-js'
import dotenv from 'dotenv'

const supabaseUrl = process.env.SUPABASE_URL
const supabaseKey = process.env.SUPABASE_KEY
const supabase = createClient(supabaseUrl, supabaseKey)


dotenv.config()

// Function to trigger the Magic Link
async function sendMagicLink(userEmail) {
  const { data, error } = await supabase.auth.signInWithOtp({
    email: userEmail,
    options: {
      emailRedirectTo: 'http://localhost:3000', 
    },
  })

  if (error) {
    console.error('Error sending magic link:', error.message)
    return false
  }
  
  console.log('Magic link sent successfully! Check your inbox.')
  return true
}
