import React, { useState, useEffect } from 'react';
import './App.css';
import { Card } from './components/ui/card';
import { Button } from './components/ui/button';
import { Progress } from './components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Badge } from './components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from './components/ui/dialog';
import { Textarea } from './components/ui/textarea';
import { Save, Download, Upload, Clock, CheckCircle } from 'lucide-react';

const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

function App() {
  const [playerData, setPlayerData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [clickAnimation, setClickAnimation] = useState(false);
  const [playerId] = useState('player-' + Math.random().toString(36).substr(2, 9));
  const [saveStatus, setSaveStatus] = useState('saved'); // 'saving', 'saved', 'error'
  const [showExportDialog, setShowExportDialog] = useState(false);
  const [showImportDialog, setShowImportDialog] = useState(false);
  const [exportData, setExportData] = useState('');
  const [importData, setImportData] = useState('');
  const [notification, setNotification] = useState('');

  // Show notification
  const showNotification = (message, duration = 3000) => {
    setNotification(message);
    setTimeout(() => setNotification(''), duration);
  };

  // Auto-save to local storage
  const saveToLocalStorage = (data) => {
    try {
      localStorage.setItem(`clicker_game_${playerId}`, JSON.stringify({
        ...data,
        saved_at: new Date().toISOString()
      }));
    } catch (error) {
      console.error('Failed to save to local storage:', error);
    }
  };

  // Load from local storage
  const loadFromLocalStorage = () => {
    try {
      const saved = localStorage.getItem(`clicker_game_${playerId}`);
      if (saved) {
        return JSON.parse(saved);
      }
    } catch (error) {
      console.error('Failed to load from local storage:', error);
    }
    return null;
  };

  // Manual save
  const handleManualSave = async () => {
    setSaveStatus('saving');
    try {
      const response = await fetch(`${API_BASE_URL}/api/save`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ player_id: playerId }),
      });
      
      if (response.ok) {
        const result = await response.json();
        setSaveStatus('saved');
        showNotification('Game saved successfully!');
        
        // Update player data to get new save time
        fetchPlayerData();
      } else {
        setSaveStatus('error');
        showNotification('Failed to save game', 5000);
      }
    } catch (error) {
      console.error('Error saving:', error);
      setSaveStatus('error');
      showNotification('Failed to save game', 5000);
    }
  };

  // Export save data
  const handleExport = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/export/${playerId}`);
      if (response.ok) {
        const result = await response.json();
        setExportData(JSON.stringify(result.save_data, null, 2));
        setShowExportDialog(true);
        showNotification('Save data exported successfully!');
      }
    } catch (error) {
      console.error('Error exporting:', error);
      showNotification('Failed to export save data', 5000);
    }
  };

  // Import save data
  const handleImport = async () => {
    try {
      const saveData = JSON.parse(importData);
      const response = await fetch(`${API_BASE_URL}/api/import`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          player_id: playerId,
          save_data: saveData
        }),
      });
      
      if (response.ok) {
        const result = await response.json();
        setShowImportDialog(false);
        setImportData('');
        showNotification('Save data imported successfully!');
        
        // Refresh player data
        fetchPlayerData();
      } else {
        const error = await response.json();
        showNotification(`Import failed: ${error.detail}`, 5000);
      }
    } catch (error) {
      console.error('Error importing:', error);
      showNotification('Invalid save data format', 5000);
    }
  };

  // Copy export data to clipboard
  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(exportData);
      showNotification('Save data copied to clipboard!');
    } catch (error) {
      // Fallback for browsers that don't support clipboard API
      const textArea = document.createElement('textarea');
      textArea.value = exportData;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      showNotification('Save data copied to clipboard!');
    }
  };

  // Fetch player data
  const fetchPlayerData = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/player/${playerId}`);
      if (response.ok) {
        const data = await response.json();
        setPlayerData(data);
        
        // Auto-save to local storage
        saveToLocalStorage(data);
      }
    } catch (error) {
      console.error('Error fetching player data:', error);
    } finally {
      setLoading(false);
    }
  };

  // Handle click
  const handleClick = async (e) => {
    if (!playerData || playerData.energy < 2) return;
    
    // Animate click
    setClickAnimation(true);
    setTimeout(() => setClickAnimation(false), 200);
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/click`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ player_id: playerId }),
      });
      
      if (response.ok) {
        const result = await response.json();
        setPlayerData(prev => ({
          ...prev,
          points: result.new_points,
          points_formatted: result.new_points_formatted,
          energy: result.new_energy
        }));
      }
    } catch (error) {
      console.error('Error clicking:', error);
    }
  };

  // Handle upgrade purchase
  const handleUpgrade = async () => {
    if (!playerData || playerData.points < playerData.next_upgrade_cost) return;
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/upgrade`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          player_id: playerId,
          upgrade_level: playerData.upgrade_level
        }),
      });
      
      if (response.ok) {
        const result = await response.json();
        setPlayerData(prev => ({
          ...prev,
          points: result.new_points,
          points_formatted: result.new_points_formatted,
          upgrade_level: result.new_upgrade_level,
          points_per_click: result.new_points_per_click
        }));
        // Refresh full data to get new upgrade cost
        fetchPlayerData();
      }
    } catch (error) {
      console.error('Error purchasing upgrade:', error);
    }
  };

  // Handle character advancement
  const handleAdvancement = async () => {
    if (!playerData || !playerData.can_advance) return;
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/advance`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ player_id: playerId }),
      });
      
      if (response.ok) {
        // Refresh all data after advancement
        fetchPlayerData();
      }
    } catch (error) {
      console.error('Error advancing character:', error);
    }
  };

  // Auto-refresh player data every 30 seconds for passive income
  useEffect(() => {
    fetchPlayerData();
    const interval = setInterval(fetchPlayerData, 30000);
    return () => clearInterval(interval);
  }, []);

  // Auto-refresh energy every 10 seconds
  useEffect(() => {
    const energyInterval = setInterval(() => {
      if (playerData && playerData.energy < playerData.max_energy) {
        fetchPlayerData();
      }
    }, 10000);
    return () => clearInterval(energyInterval);
  }, [playerData]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-xl font-inter">Loading...</div>
      </div>
    );
  }

  const energyPercentage = playerData ? (playerData.energy / playerData.max_energy) * 100 : 0;

  return (
    <div className="min-h-screen bg-gray-100" onClick={handleClick}>
      <div className="container mx-auto px-4 py-8 max-w-4xl font-inter">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">Clicker Game</h1>
          <div className="text-6xl font-bold text-gray-900 mb-2" style={{color: '#51FED6'}}>
            {playerData?.points_formatted || '0'}
          </div>
          <div className="text-lg text-gray-600">Points</div>
        </div>

        {/* Main Game Area */}
        <div className={`mb-8 transition-transform duration-200 ${clickAnimation ? 'scale-95' : 'scale-100'}`}>
          <Card className="p-8 text-center bg-white shadow-lg hover:shadow-xl transition-shadow cursor-pointer">
            <div className="mb-4">
              <div className="text-2xl font-semibold text-gray-700 mb-2">
                Tap anywhere to earn points!
              </div>
              <div className="text-lg" style={{color: '#51FED6'}}>
                +{playerData?.points_per_click || 1} points per click
              </div>
            </div>
            
            {/* Energy Bar */}
            <div className="mb-4">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium text-gray-600">Energy</span>
                <span className="text-sm text-gray-600">
                  {playerData?.energy || 0}/{playerData?.max_energy || 100}
                </span>
              </div>
              <Progress value={energyPercentage} className="h-3" />
              {playerData?.energy < 2 && (
                <div className="text-sm text-red-500 mt-1">Not enough energy! (2 energy per click)</div>
              )}
            </div>
          </Card>
        </div>

        {/* Tabs */}
        <Tabs defaultValue="game" className="w-full">
          <TabsList className="grid w-full grid-cols-3 mb-6">
            <TabsTrigger value="game">Game</TabsTrigger>
            <TabsTrigger value="store">Store</TabsTrigger>
            <TabsTrigger value="character">Character</TabsTrigger>
          </TabsList>

          <TabsContent value="game">
            <Card className="p-6">
              <h2 className="text-2xl font-semibold mb-4 text-gray-800">Game Stats</h2>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-sm text-gray-600">Total Points</div>
                  <div className="text-xl font-bold">{playerData?.points_formatted || '0'}</div>
                </div>
                <div>
                  <div className="text-sm text-gray-600">Points per Click</div>
                  <div className="text-xl font-bold" style={{color: '#51FED6'}}>
                    {playerData?.points_per_click || 1}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-600">Energy</div>
                  <div className="text-xl font-bold">
                    {playerData?.energy || 0}/{playerData?.max_energy || 100}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-600">Upgrade Level</div>
                  <div className="text-xl font-bold">{playerData?.upgrade_level || 0}</div>
                </div>
              </div>
            </Card>
          </TabsContent>

          <TabsContent value="store">
            <Card className="p-6">
              <h2 className="text-2xl font-semibold mb-4 text-gray-800">Upgrades</h2>
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 border rounded-lg">
                  <div>
                    <div className="font-medium">Click Power Upgrade</div>
                    <div className="text-sm text-gray-600">
                      Level {playerData?.upgrade_level || 0} → {(playerData?.upgrade_level || 0) + 1}
                    </div>
                    <div className="text-sm" style={{color: '#51FED6'}}>
                      +10% of cost as points per click
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-bold text-lg mb-2">
                      {playerData?.next_upgrade_cost_formatted || '100'}
                    </div>
                    <Button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleUpgrade();
                      }}
                      disabled={!playerData || playerData.points < playerData.next_upgrade_cost}
                      style={{backgroundColor: playerData?.points >= playerData?.next_upgrade_cost ? '#51FED6' : undefined}}
                      className="hover:opacity-90"
                    >
                      Upgrade
                    </Button>
                  </div>
                </div>
              </div>
            </Card>
          </TabsContent>

          <TabsContent value="character">
            <Card className="p-6">
              <h2 className="text-2xl font-semibold mb-4 text-gray-800">Character Progression</h2>
              <div className="space-y-6">
                {/* Current Character */}
                <div className="text-center">
                  <Badge variant="outline" className="text-lg px-4 py-2 mb-2" style={{borderColor: '#51FED6', color: '#51FED6'}}>
                    Level {playerData?.character_level || 1}
                  </Badge>
                  <div className="text-3xl font-bold text-gray-800 mb-2">
                    {playerData?.character_name || 'Junior'}
                  </div>
                  <div className="text-lg text-gray-600 mb-4">
                    {playerData?.character_multiplier || 1}x Multiplier
                  </div>
                  <div className="text-sm text-gray-500">
                    Max Energy: {playerData?.max_energy || 100}
                  </div>
                </div>

                {/* Advancement */}
                {playerData?.advancement_cost && (
                  <div className="text-center pt-4 border-t">
                    <div className="mb-4">
                      <div className="text-lg font-medium text-gray-700 mb-2">Next Level</div>
                      <div className="text-sm text-gray-600 mb-2">
                        Cost: {playerData.advancement_cost_formatted}
                      </div>
                      <div className="text-xs text-red-500 mb-4">
                        ⚠️ Advancement will reset your points and upgrades!
                      </div>
                    </div>
                    <Button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleAdvancement();
                      }}
                      disabled={!playerData?.can_advance}
                      style={{backgroundColor: playerData?.can_advance ? '#51FED6' : undefined}}
                      className="hover:opacity-90"
                    >
                      Advance Character
                    </Button>
                  </div>
                )}

                {/* Character Levels Overview */}
                <div className="pt-4 border-t">
                  <h3 className="font-medium text-gray-700 mb-3">All Levels</h3>
                  <div className="grid grid-cols-1 gap-2 text-sm">
                    {[
                      {level: 1, name: 'Junior', mult: '1x', energy: 100},
                      {level: 2, name: 'Deishi', mult: '2x', energy: 150},
                      {level: 3, name: 'Shugo', mult: '3x', energy: 200},
                      {level: 4, name: 'Seishi', mult: '5x', energy: 250},
                      {level: 5, name: 'Shihan', mult: '8x', energy: 300}
                    ].map(char => (
                      <div 
                        key={char.level} 
                        className={`flex justify-between p-2 rounded ${
                          playerData?.character_level === char.level 
                            ? 'bg-cyan-50 border border-cyan-200' 
                            : 'bg-gray-50'
                        }`}
                      >
                        <span>{char.name}</span>
                        <span>{char.mult} • {char.energy} energy</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

export default App;