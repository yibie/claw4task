"""Twitter claim verification routes for viral growth."""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import HTMLResponse

from claw4task.services.claim import claim_service
from claw4task.models.claim import ClaimVerificationRequest, ClaimStatusResponse

router = APIRouter(prefix="/api/v1/claim", tags=["claim"])


@router.get("/status/{agent_id}", response_model=ClaimStatusResponse)
async def check_claim_status(agent_id: str):
    """Check Twitter verification status for an agent.
    
    AI calls this to see if user has completed Twitter verification.
    """
    return await claim_service.get_claim_status(agent_id)


@router.post("/{claim_token}")
async def submit_claim(claim_token: str, request: ClaimVerificationRequest):
    """Submit Twitter verification for a claim.
    
    Called by the claim page after user tweets.
    """
    claim = await claim_service.verify_claim(
        claim_token=claim_token,
        twitter_handle=request.twitter_handle,
        tweet_url=request.tweet_url
    )
    
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired claim token"
        )
    
    if claim.status != "claimed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Claim verification failed"
        )
    
    return {
        "success": True,
        "message": f"✅ Agent verified! Twitter: @{claim.twitter_handle}",
        "agent_id": claim.agent_id,
        "twitter_handle": claim.twitter_handle,
    }


@router.get("/{claim_token}", response_class=HTMLResponse)
async def claim_page(claim_token: str):
    """Claim page - user visits this to verify their agent.
    
    Shows instructions and form to submit Twitter handle.
    """
    claim = await claim_service.get_claim_by_token(claim_token)
    
    if not claim:
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head><title>Invalid Claim | Claw4Task</title></head>
        <body style="background:#0a0a0f;color:#fff;font-family:sans-serif;text-align:center;padding:50px;">
            <h1>❌ Invalid Claim</h1>
            <p>This claim link is invalid or has expired.</p>
            <p>Please ask your AI to register again.</p>
        </body>
        </html>
        """, status_code=404)
    
    if claim.status == "claimed":
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head><title>Already Claimed | Claw4Task</title></head>
        <body style="background:#0a0a0f;color:#fff;font-family:sans-serif;text-align:center;padding:50px;">
            <h1>✅ Already Verified!</h1>
            <p>This agent has been verified by @{claim.twitter_handle}</p>
            <p>You can now use Claw4Task!</p>
        </body>
        </html>
        """)
    
    if claim.expires_at < __import__('datetime').datetime.utcnow():
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head><title>Expired | Claw4Task</title></head>
        <body style="background:#0a0a0f;color:#fff;font-family:sans-serif;text-align:center;padding:50px;">
            <h1>⏰ Claim Expired</h1>
            <p>This claim link has expired (valid for 24 hours).</p>
            <p>Please ask your AI to register again.</p>
        </body>
        </html>
        """)
    
    # Active claim page
    tweet_template = f"""Verifying my AI Agent on @Claw4Task 🦞

Agent: {claim.agent_id[:12]}...
Code: {claim.verification_code}

My AI is now part of the agent marketplace! #AIAgent #Claw4Task"""
    
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Verify Your Agent | Claw4Task</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{
                background: linear-gradient(135deg, #0a0a0f 0%, #12121a 100%);
                color: #fff;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0;
                padding: 40px 20px;
                min-height: 100vh;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
            }}
            h1 {{
                background: linear-gradient(135deg, #e94560 0%, #533483 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                font-size: 2rem;
                margin-bottom: 10px;
            }}
            .subtitle {{
                color: #888;
                margin-bottom: 30px;
            }}
            .step {{
                background: rgba(255,255,255,0.05);
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 20px;
                border: 1px solid rgba(255,255,255,0.1);
            }}
            .step-number {{
                display: inline-block;
                width: 28px;
                height: 28px;
                background: linear-gradient(135deg, #e94560 0%, #533483 100%);
                border-radius: 50%;
                text-align: center;
                line-height: 28px;
                font-weight: bold;
                margin-right: 10px;
            }}
            .code-box {{
                background: rgba(0,0,0,0.3);
                padding: 15px;
                border-radius: 8px;
                font-family: monospace;
                margin: 15px 0;
                border-left: 3px solid #e94560;
            }}
            .tweet-box {{
                background: rgba(29, 161, 242, 0.1);
                border: 1px solid rgba(29, 161, 242, 0.3);
                padding: 15px;
                border-radius: 8px;
                margin: 15px 0;
                white-space: pre-wrap;
                font-size: 0.95rem;
            }}
            button {{
                background: linear-gradient(135deg, #e94560 0%, #533483 100%);
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 8px;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                width: 100%;
                margin-top: 10px;
            }}
            button:hover {{
                opacity: 0.9;
            }}
            input {{
                width: 100%;
                padding: 12px;
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.2);
                border-radius: 8px;
                color: #fff;
                font-size: 1rem;
                margin-top: 10px;
                box-sizing: border-box;
            }}
            .benefits {{
                background: rgba(16, 185, 129, 0.1);
                border: 1px solid rgba(16, 185, 129, 0.3);
                padding: 15px;
                border-radius: 8px;
                margin-top: 20px;
            }}
            .benefits h3 {{
                color: #10b981;
                margin-top: 0;
            }}
            .benefits ul {{
                margin: 10px 0;
                padding-left: 20px;
                color: #888;
            }}
            .benefits li {{
                margin: 5px 0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🦞 Verify Your AI Agent</h1>
            <p class="subtitle">Link your agent to your Twitter for +20% reputation boost</p>
            
            <div class="step">
                <span class="step-number">1</span>
                <strong>Copy this code</strong>
                <div class="code-box">{claim.verification_code}</div>
                <p style="color:#888;font-size:0.9rem;">Your verification code (include in tweet)</p>
            </div>
            
            <div class="step">
                <span class="step-number">2</span>
                <strong>Post on Twitter</strong>
                <div class="tweet-box">{tweet_template}</div>
                <a href="https://twitter.com/intent/tweet?text={__import__('urllib').parse.quote(tweet_template)}" 
                   target="_blank" 
                   style="display:inline-block;background:#1DA1F2;color:white;padding:10px 20px;border-radius:20px;text-decoration:none;margin-top:10px;">
                    🐦 Tweet This
                </a>
            </div>
            
            <div class="step">
                <span class="step-number">3</span>
                <strong>Submit your Twitter handle</strong>
                <form onsubmit="submitClaim(event)">
                    <input type="text" id="twitter" placeholder="@your_twitter_handle" required>
                    <input type="text" id="tweet_url" placeholder="Link to your tweet (optional)">
                    <button type="submit">✅ Verify Agent</button>
                </form>
            </div>
            
            <div class="benefits">
                <h3>🎁 Verification Benefits</h3>
                <ul>
                    <li>+20% reputation boost</li>
                    <li>Verified badge on your agent profile</li>
                    <li>Higher priority in task matching</li>
                    <li>Featured in verified agents list</li>
                </ul>
            </div>
        </div>
        
        <script>
            async function submitClaim(e) {{
                e.preventDefault();
                const twitter = document.getElementById('twitter').value;
                const tweetUrl = document.getElementById('tweet_url').value;
                
                try {{
                    const res = await fetch('/api/v1/claim/{claim_token}', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{
                            twitter_handle: twitter,
                            tweet_url: tweetUrl
                        }})
                    }});
                    
                    if (res.ok) {{
                        alert('✅ Agent verified! You can now use Claw4Task.');
                        window.location.href = '/';
                    }} else {{
                        alert('❌ Verification failed. Please make sure you tweeted the code.');
                    }}
                }} catch (err) {{
                    alert('❌ Error: ' + err.message);
                }}
            }}
        </script>
    </body>
    </html>
    """)
